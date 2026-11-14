import time
import collections
import math
import numpy as np
import supervision as sv
import config
from core.entity import TrafficEntity

class TrafficTrackerManager:
    """
    Bộ quản lý theo dõi và ghép nối đa đối tượng (Multi-Object Tracker & Rider Matching).
    - Tích hợp mô hình bám đuôi SOTA ByteTrack
    - Quản lý vòng đời của các thực thể TrafficEntity
    - Thuật toán ghép nối Rider với cơ chế Hysteresis Deque(maxlen=10) (B2)
    - Phân định rõ 3 vai trò: vehicle, rider, pedestrian (A3)
    - Stable-ID: nếu ByteTrack cấp ID mới sau occlusion, thử gán lại ID cũ
      dựa trên class + vị trí dự đoán + thời gian (không cần model ReID nặng).
    - Tự động dọn dẹp bộ nhớ và hỗ trợ làm mới khi video tua lại (loop)
    """
    def __init__(self, track_activation_thresh=0.25, lost_buffer=None, frame_rate=30,
                 match_threshold=None, enable_reid=None,
                 reid_ttl_frames=None, reid_min_score=None, entity_ttl=None,
                 reid_gate=None):
        self.track_activation_thresh = track_activation_thresh
        self.lost_buffer = (lost_buffer if lost_buffer is not None
                            else getattr(config, "TRACK_LOST_BUFFER", 30))
        self.frame_rate = frame_rate
        self.match_threshold = (match_threshold if match_threshold is not None
                                else getattr(config, "TRACK_MATCH_THRESHOLD", 0.8))
        self.enable_reid = (enable_reid if enable_reid is not None
                            else getattr(config, "TRACK_REID_ENABLED", True))
        # TTL tính theo SỐ FRAME đã xử lý (không phải giây) để kết quả không phụ thuộc
        # tốc độ máy: 45 frame ~ 1.5s video 30fps.
        self.reid_ttl_frames = (reid_ttl_frames if reid_ttl_frames is not None
                                else getattr(config, "TRACK_REID_TTL_FRAMES", 45))
        self.reid_min_score = (reid_min_score if reid_min_score is not None
                               else getattr(config, "TRACK_REID_MIN_SCORE", 0.20))
        self.entity_ttl = (entity_ttl if entity_ttl is not None
                           else getattr(config, "TRACK_ENTITY_TTL_SEC", 15.0))
        # Bán kính cổng tìm kiếm, tính theo lần đường chéo box cuối (2.0 = vừa phải).
        self.reid_gate = (reid_gate if reid_gate is not None
                          else getattr(config, "TRACK_REID_GATE", 2.0))

        self._init_tracker()
        self.entities = {} # {stable_id: TrafficEntity}
        self.riders_map = {} # {person_stable_id: moto_stable_id}
        self.rider_history = {} # {person_stable_id: deque(maxlen=10)} - B2: Hysteresis
        self.id_map = {} # {raw_byte_track_id: stable_id}
        self.track_memory = {} # {stable_id: last box/velocity/time} - phục vụ re-ID
        self.frame_count = 0

    def _init_tracker(self):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=self.track_activation_thresh,
            lost_track_buffer=self.lost_buffer,
            minimum_matching_threshold=self.match_threshold,
            frame_rate=self.frame_rate
        )

    def reset(self):
        """Khởi tạo lại toàn bộ bộ nhớ khi video loop hoặc đổi nguồn camera"""
        self._init_tracker()
        self.entities.clear()
        self.riders_map.clear()
        self.rider_history.clear()
        self.id_map.clear()
        self.track_memory.clear()
        self.frame_count = 0
        print("🔄 [TRACKER] Đã làm mới toàn bộ bộ nhớ theo dõi đối tượng cho chu kỳ mới.")

    @staticmethod
    def _box_iou(box_a, box_b):
        xa = max(box_a[0], box_b[0])
        ya = max(box_a[1], box_b[1])
        xb = min(box_a[2], box_b[2])
        yb = min(box_a[3], box_b[3])
        inter = max(0.0, xb - xa) * max(0.0, yb - ya)
        area_a = max(1.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
        area_b = max(1.0, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
        return inter / max(1.0, area_a + area_b - inter)

    @staticmethod
    def _box_center(box):
        return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)

    @staticmethod
    def _box_diag(box):
        return math.hypot(box[2] - box[0], box[3] - box[1])

    def _reid_score(self, mem, box, cls_name):
        """
        Điểm khớp giữa track đã mất và detection mới.
        Chỉ xét cùng class; dùng IoU với box cuối + khoảng cách tới vị trí dự đoán.
        """
        if mem.get("cls") != cls_name:
            return None
        age_frames = self.frame_count - mem.get("frame", self.frame_count)
        if age_frames > self.reid_ttl_frames:
            return None

        cx, cy = self._box_center(box)
        dt = min(60, max(1, age_frames))
        vx, vy = mem.get("velocity", (0.0, 0.0))
        pred_cx = mem["center"][0] + vx * dt
        pred_cy = mem["center"][1] + vy * dt
        dist = math.hypot(cx - pred_cx, cy - pred_cy)
        diag = max(self._box_diag(mem["box"]), self._box_diag(box), 1.0)
        gate = max(1.0, self.reid_gate) * diag
        dist_score = max(0.0, 1.0 - dist / gate)
        iou_score = self._box_iou(mem["box"], box)

        # Ngoài cổng tìm kiếm coi như không phải cùng một đối tượng.
        if dist > gate:
            return None
        return 0.6 * iou_score + 0.4 * dist_score

    def _apply_stable_ids(self, tracked_list):
        """
        Ánh xạ ID thô của ByteTrack -> stable ID.
        - ID đã biết: dùng lại stable ID.
        - ID mới: thử ghép với track vừa mất (cùng class, gần vị trí dự đoán, còn TTL).
        - Không ghép được: dùng chính ID thô làm stable ID.
        """
        if not tracked_list:
            return tracked_list

        active_stable = set()
        unmatched = []

        for t in tracked_list:
            raw_id = int(t["tracker_id"])
            t["raw_tracker_id"] = raw_id
            if raw_id in self.id_map:
                t["tracker_id"] = self.id_map[raw_id]
                active_stable.add(t["tracker_id"])
            else:
                unmatched.append(t)

        if not unmatched:
            return self._dedup_stable_ids(tracked_list)

        if not self.enable_reid:
            for t in unmatched:
                raw_id = t["raw_tracker_id"]
                self.id_map[raw_id] = raw_id
                t["tracker_id"] = raw_id
            return self._dedup_stable_ids(tracked_list)

        # Ứng viên: track đã mất, không còn active, còn trong TTL.
        candidates = []
        for stable_id, mem in self.track_memory.items():
            if stable_id in active_stable:
                continue
            if self.frame_count - mem.get("frame", -10**9) <= self.reid_ttl_frames:
                candidates.append((stable_id, mem))

        used = set(active_stable)
        # Ưu tiên detection có confidence cao trước; greedy 1-1 để tránh 2 track mới
        # cùng nhận một ID cũ.
        for t in sorted(unmatched, key=lambda x: -float(x.get("score", 0.0))):
            raw_id = t["raw_tracker_id"]
            best_id, best_score, best_mem = None, -1.0, None
            for stable_id, mem in candidates:
                if stable_id in used:
                    continue
                score = self._reid_score(mem, t["box"], t["class_name"])
                if score is not None and score > best_score:
                    best_id, best_score, best_mem = stable_id, score, mem

            if best_id is not None and best_score >= self.reid_min_score:
                # Nếu raw cũ của stable ID này còn sống, cắt liên kết để tránh
                # hai raw track cùng trỏ về một stable ID trong các frame sau.
                old_raw = best_mem.get("raw") if best_mem else None
                if old_raw is not None and old_raw != raw_id:
                    self.id_map.pop(old_raw, None)
                self.id_map[raw_id] = best_id
                t["tracker_id"] = best_id
                t["reidentified"] = True
                used.add(best_id)
            else:
                self.id_map[raw_id] = raw_id
                t["tracker_id"] = raw_id
                used.add(raw_id)

        return self._dedup_stable_ids(tracked_list)

    def _dedup_stable_ids(self, tracked_list):
        """
        Lưới an toàn: mỗi stable ID chỉ được xuất hiện một lần trong một frame.
        Nếu trùng, giữ detection có confidence cao nhất và trả detection còn lại
        về ID thô của nó.
        """
        by_stable = {}
        for t in tracked_list:
            by_stable.setdefault(t["tracker_id"], []).append(t)
        for stable_id, group in by_stable.items():
            if len(group) <= 1:
                continue
            group.sort(key=lambda x: -float(x.get("score", 0.0)))
            for t in group[1:]:
                raw_id = t["raw_tracker_id"]
                self.id_map[raw_id] = raw_id
                t["tracker_id"] = raw_id
                t.pop("reidentified", None)
        return tracked_list

    def _remember_track(self, tracked, now):
        """Lưu box/vận tốc/thời điểm cuối của stable ID để phục vụ re-ID."""
        stable_id = tracked["tracker_id"]
        box = tracked["box"]
        cx, cy = self._box_center(box)
        mem = self.track_memory.get(stable_id)
        if mem is None:
            self.track_memory[stable_id] = {
                "box": list(box),
                "cls": tracked["class_name"],
                "center": (cx, cy),
                "velocity": (0.0, 0.0),
                "ts": now,
                "frame": self.frame_count,
                "raw": tracked.get("raw_tracker_id", stable_id),
            }
            return

        dt = max(1, self.frame_count - mem.get("frame", self.frame_count))
        vx = (cx - mem["center"][0]) / dt
        vy = (cy - mem["center"][1]) / dt
        old_vx, old_vy = mem.get("velocity", (0.0, 0.0))
        mem["velocity"] = (0.7 * old_vx + 0.3 * vx, 0.7 * old_vy + 0.3 * vy)
        mem["box"] = list(box)
        mem["cls"] = tracked["class_name"]
        mem["center"] = (cx, cy)
        mem["ts"] = now
        mem["frame"] = self.frame_count
        mem["raw"] = tracked.get("raw_tracker_id", stable_id)

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
        self.frame_count += 1
        now = time.time()

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

        # 2. Ánh xạ ID thô -> stable ID (re-ID sau occlusion) rồi mới ghép rider
        tracked_list = self._apply_stable_ids(tracked_list)
        self.riders_map = self.find_riders(tracked_list, is_standalone=is_standalone)

        # 3. Đồng bộ hóa với danh sách TrafficEntity
        active_entities = []
        active_ids = set()

        for t in tracked_list:
            tr_id = t["tracker_id"]
            box = t["box"]
            raw_cls = t["class_name"]
            conf = t["score"]
            was_reidentified = bool(t.get("reidentified", False))
            active_ids.add(tr_id)

            if tr_id not in self.entities:
                entity = TrafficEntity(tr_id, box, raw_cls, conf, stop_line_y=stop_line_y)
                self.entities[tr_id] = entity
            else:
                entity = self.entities[tr_id]
                entity.update(box, raw_cls, conf, stop_line_y=stop_line_y)
                if was_reidentified:
                    # Vừa nối lại sau occlusion: bỏ qua kiểm tra cắt vạch trên frame đầu
                    # để tránh tính nhầm một vi phạm dựa trên quỹ đạo bị khuyết.
                    entity.prev_leading_edge_y = entity.leading_edge_y

            self._remember_track(t, now)

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

        # 4. Dọn dẹp thực thể cũ đã biến mất quá entity_ttl (Tránh rò rỉ bộ nhớ).
        # Giữ lâu hơn 3.0s để còn state cho stable-ID nối lại sau occlusion.
        stale_ids = [
            tid for tid, ent in self.entities.items()
            if tid not in active_ids and (now - ent.last_updated) > self.entity_ttl
        ]
        for tid in stale_ids:
            self.entities.pop(tid, None)
            self.rider_history.pop(tid, None)
            self.track_memory.pop(tid, None)
            for raw_id, stable_id in list(self.id_map.items()):
                if stable_id == tid:
                    self.id_map.pop(raw_id, None)

        # Dọn ký ức re-ID mồ côi (không còn entity) quá TTL.
        for stable_id, mem in list(self.track_memory.items()):
            if stable_id not in self.entities and (now - mem.get("ts", 0.0)) > self.entity_ttl:
                self.track_memory.pop(stable_id, None)

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



