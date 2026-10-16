import time
import collections
import numpy as np
import supervision as sv
from core.entity import TrafficEntity

class TrafficTrackerManager:
    """
    Bộ quản lý theo dõi và ghép nối đa đối tượng (Multi-Object Tracker & Rider Matching).
    - Tích hợp mô hình bám đuôi SOTA ByteTrack
    - Quản lý vòng đời của các thực thể TrafficEntity
    - Thuật toán ghép nối Rider với cơ chế Hysteresis Deque(maxlen=10) (B2)
    - Phân định rõ 3 vai trò: vehicle, rider, pedestrian (A3)
    - Tự động dọn dẹp bộ nhớ và hỗ trợ làm mới khi video tua lại (loop)
    """
    def __init__(self, track_activation_thresh=0.25, lost_buffer=30, frame_rate=30):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_thresh,
            lost_track_buffer=lost_buffer,
            minimum_matching_threshold=0.8,
            frame_rate=frame_rate
        )
        self.entities = {} # {tracker_id: TrafficEntity}
        self.riders_map = {} # {person_tr_id: moto_tr_id}
        self.rider_history = {} # {person_tr_id: deque(maxlen=10)} - B2: Hysteresis

    def reset(self):
        """Khởi tạo lại toàn bộ bộ nhớ khi video loop hoặc đổi nguồn camera"""
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=30
        )
        self.entities.clear()
        self.riders_map.clear()
        self.rider_history.clear()
        print("🔄 [TRACKER] Đã làm mới toàn bộ bộ nhớ theo dõi đối tượng cho chu kỳ mới.")

    def find_riders(self, raw_tracked_objects, is_standalone=False):
        """
        Thuật toán ghép nối Người với Phương tiện 2 bánh (Spatial Matching):
        - Hỗ trợ cả motorcycle và bicycle/scooter (thường bị YOLO nhận nhầm qua lại)
        - is_standalone=True: Cho phép test cá nhân tại nhà (webcam/ảnh tĩnh)
        Trả về dict: {person_tr_id: moto_tr_id}
        """
        persons = [o for o in raw_tracked_objects if o["class_name"] == "person"]
        two_wheelers = [o for o in raw_tracked_objects if o["class_name"] in ["motorcycle", "bicycle"]]

        if is_standalone:
            return {p["tracker_id"]: None for p in persons}

        if len(two_wheelers) == 0:
            return {}

        riders = {}
        for p in persons:
            px1, py1, px2, py2 = p["box"]
            p_area = max(1.0, (px2 - px1) * (py2 - py1))
            pcx = (px1 + px2) / 2.0

            best_moto_id = None
            max_overlap = 0.0

            for m in two_wheelers:
                mx1, my1, mx2, my2 = m["box"]
                ix = max(0.0, min(px2, mx2) - max(px1, mx1))
                iy = max(0.0, min(py2, my2) - max(py1, my1))
                inter_area = ix * iy
                overlap_ratio = inter_area / p_area

                # Tiêu chuẩn ghép nối:
                # 1. Độ chồng lấn diện tích >= 15%
                # 2. Tâm ngang của người nằm trong phạm vi thân xe (dung sai 20px)
                # 3. Đỉnh đầu người nằm ở nửa trên thân xe
                if overlap_ratio > 0.15 and (mx1 - 20 <= pcx <= mx2 + 20) and py1 < (my1 + (my2 - my1) * 0.7):
                    if overlap_ratio > max_overlap:
                        max_overlap = overlap_ratio
                        best_moto_id = m["tracker_id"]

            if best_moto_id is not None:
                riders[p["tracker_id"]] = best_moto_id

        return riders

    def update(self, detections_list, stop_line_y=468, is_standalone=False):
        """
        Cập nhật ByteTrack với các phát hiện từ YOLO, đồng bộ danh sách TrafficEntity.
        Trả về: Danh sách các thực thể TrafficEntity đang hoạt động trong frame hiện tại.
        """
        # 1. Chuyển đổi dữ liệu sang supervision.Detections
        if not detections_list:
            empty_det = sv.Detections.empty()
            raw_tracks = self.tracker.update_with_detections(empty_det)
            tracked_list = []
        else:
            boxes = np.array([d['box'] for d in detections_list], dtype=float)
            scores = np.array([d['score'] for d in detections_list], dtype=float)
            class_ids = np.array([d.get('class_id', 0) for d in detections_list], dtype=int)
            class_names = [d['class_name'] for d in detections_list]

            det_sv = sv.Detections(
                xyxy=boxes,
                confidence=scores,
                class_id=class_ids,
                data={"class_name": np.array(class_names)}
            )
            raw_tracks = self.tracker.update_with_detections(det_sv)

            tracked_list = []
            if len(raw_tracks) > 0 and raw_tracks.tracker_id is not None:
                for xyxy, tr_id, cls_name, conf in zip(
                    raw_tracks.xyxy,
                    raw_tracks.tracker_id,
                    raw_tracks.data["class_name"],
                    raw_tracks.confidence
                ):
                    tracked_list.append({
                        "box": [round(float(c), 2) for c in xyxy],
                        "tracker_id": int(tr_id),
                        "class_name": str(cls_name).lower(),
                        "score": round(float(conf), 4)
                    })

        # 2. Chạy thuật toán ghép nối Rider
        self.riders_map = self.find_riders(tracked_list, is_standalone=is_standalone)

        # 3. Đồng bộ hóa với danh sách TrafficEntity
        active_entities = []
        active_ids = set()

        for t in tracked_list:
            tr_id = t["tracker_id"]
            box = t["box"]
            raw_cls = t["class_name"]
            conf = t["score"]
            active_ids.add(tr_id)

            if tr_id not in self.entities:
                entity = TrafficEntity(tr_id, box, raw_cls, conf, stop_line_y=stop_line_y)
                self.entities[tr_id] = entity
            else:
                entity = self.entities[tr_id]
                entity.update(box, raw_cls, conf, stop_line_y=stop_line_y)

            # Phân định vai trò (A3, B2):
            if entity.stable_class in {"car", "motorcycle", "bus", "truck"}:
                entity.set_role("vehicle")
            elif is_standalone:
                entity.set_role("rider", moto_id=None)
            else:
                # Entity person: Áp dụng Hysteresis lọc nhiễu B2 với deque(maxlen=10)
                if tr_id not in self.rider_history:
                    self.rider_history[tr_id] = collections.deque(maxlen=10)

                is_matched = (tr_id in self.riders_map)
                self.rider_history[tr_id].append(is_matched)
                matches_count = sum(self.rider_history[tr_id])

                # Ngưỡng vào: ghép được với xe máy >= 2 lần trong 10 frame gần nhất
                if matches_count >= 2:
                    moto_id = self.riders_map.get(tr_id)
                    entity.set_role("rider", moto_id=moto_id)
                elif matches_count == 0:
                    # Nếu không ghép được xe 2 bánh và chưa bị chốt vi phạm, đây là người đi bộ (pedestrian)
                    if not entity.violation_no_helmet:
                        entity.set_role("pedestrian")

            active_entities.append(entity)

        # 4. Dọn dẹp thực thể cũ đã biến mất quá 3.0 giây (Tránh rò rỉ bộ nhớ)
        now = time.time()
        stale_ids = [tid for tid, ent in self.entities.items() if tid not in active_ids and (now - ent.last_updated) > 3.0]
        for tid in stale_ids:
            self.entities.pop(tid, None)
            self.rider_history.pop(tid, None)

        return active_entities

    def unify_motorcycle_violations(self, entities, violation_engine):
        """
        Phương án 2: Hợp nhất vi phạm Mũ bảo hiểm về Bounding Box xe máy duy nhất.
        1. Nếu xe máy hoặc bất kỳ rider nào trên xe vi phạm không đội mũ:
           - Bounding box của xe máy mở rộng (union) bao trùm toàn bộ xe và các rider.
           - Xe máy nhận nhãn [KO MU] Xe may #{moto_id} viền đỏ rực.
           - Toàn bộ các box con (rider, người ngồi trước/sau) bên trong xe bị triệt tiêu (suppress_render = True).
        2. Nếu không có box xe máy (hoặc chạy standalone), các box rider trùng lấn trên cùng xe
           sẽ được gộp thành 1 box duy nhất, triệt tiêu box con dư thừa.
        """
        # 1. Reset thuộc tính hiển thị mỗi frame
        for e in entities:
            e.suppress_render = False
            e.render_box = list(e.box)

        # 2. Gom nhóm theo xe máy
        motorcycles = [
            e for e in entities 
            if e.stable_class in {"motorcycle", "bicycle"} or 
               (e.role == "vehicle" and e.raw_class in {"motorcycle", "bicycle"})
        ]
        moto_dict = {m.id: m for m in motorcycles}
        moto_to_riders = {m.id: [] for m in motorcycles}
        unassigned_riders = []

        for e in entities:
            if e.id in moto_dict:
                continue

            assigned_moto_id = None
            # Kiểm tra qua moto_id hoặc riders_map
            if e.moto_id in moto_dict:
                assigned_moto_id = e.moto_id
            elif self.riders_map.get(e.id) in moto_dict:
                assigned_moto_id = self.riders_map.get(e.id)
            else:
                # Kiểm tra chồng lấn không gian với các xe máy
                ex1, ey1, ex2, ey2 = e.box
                ecx = (ex1 + ex2) / 2.0
                e_area = (ex2 - ex1) * (ey2 - ey1)
                for m in motorcycles:
                    mx1, my1, mx2, my2 = m.box
                    ix = max(0.0, min(ex2, mx2) - max(ex1, mx1))
                    iy = max(0.0, min(ey2, my2) - max(ey1, my1))
                    if e_area > 0 and (ix * iy / e_area) > 0.12 and (mx1 - 35 <= ecx <= mx2 + 35):
                        assigned_moto_id = m.id
                        break

            if assigned_moto_id is not None:
                moto_to_riders[assigned_moto_id].append(e)
                e.set_role("rider", moto_id=assigned_moto_id)
            else:
                if e.role == "rider" or e.violation_no_helmet:
                    unassigned_riders.append(e)

        # 3. Hợp nhất vi phạm trên từng xe máy
        for moto_id, moto in moto_dict.items():
            riders = moto_to_riders.get(moto_id, [])

            is_violating = (
                moto.violation_no_helmet or
                moto.id in violation_engine.violating_helmets or
                any(r.violation_no_helmet or r.id in violation_engine.violating_helmets for r in riders)
            )

            if is_violating:
                moto.violation_no_helmet = True
                violation_engine.violating_helmets.add(moto.id)

                # Mở rộng bounding box bao trùm cả xe máy và tất cả riders
                all_boxes = [moto.box] + [r.box for r in riders]
                ux1 = min(b[0] for b in all_boxes)
                uy1 = min(b[1] for b in all_boxes)
                ux2 = max(b[2] for b in all_boxes)
                uy2 = max(b[3] for b in all_boxes)
                moto.render_box = [ux1, uy1, ux2, uy2]

                # Triệt tiêu toàn bộ các rider con bên trong chiếc xe vi phạm
                for r in riders:
                    r.suppress_render = True
                    r.violation_no_helmet = True
                    violation_engine.violating_helmets.add(r.id)

        # 4. Hợp nhất các rider không có box xe máy (hoặc chạy standalone)
        # Nếu có người vi phạm trên xe, gom cụm các rider đè lên nhau thành 1 box vi phạm duy nhất
        for r1 in unassigned_riders:
            if r1.suppress_render:
                continue
            r1_violating = (r1.violation_no_helmet or r1.id in violation_engine.violating_helmets)

            for r2 in unassigned_riders:
                if r2.id == r1.id or r2.suppress_render:
                    continue
                r2_violating = (r2.violation_no_helmet or r2.id in violation_engine.violating_helmets)

                if not (r1_violating or r2_violating):
                    continue

                b1 = r1.render_box
                b2 = r2.render_box
                ix = max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
                iy = max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                inter_area = ix * iy
                a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
                a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
                min_a = min(a1, a2)

                if min_a > 0 and (inter_area / min_a) > 0.20:
                    ux1 = min(b1[0], b2[0])
                    uy1 = min(b1[1], b2[1])
                    ux2 = max(b1[2], b2[2])
                    uy2 = max(b1[3], b2[3])
                    r1.render_box = [ux1, uy1, ux2, uy2]
                    r1.violation_no_helmet = True
                    r2.suppress_render = True
                    violation_engine.violating_helmets.add(r1.id)
                    violation_engine.violating_helmets.add(r2.id)



