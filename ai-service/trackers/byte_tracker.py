import numpy as np
import supervision as sv
import sys, os

# Thêm thư mục cha để đọc config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

class ByteTrackerManager:
    def __init__(self, track_activation_threshold=0.25, lost_track_buffer=30, minimum_matching_threshold=0.8, frame_rate=30):
        """
        Khởi tạo bộ bám đuôi đối tượng ByteTrack (Task 2.2):
        - track_activation_threshold: Ngưỡng kích hoạt track mới (0.25)
        - lost_track_buffer: Giữ bộ nhớ 30 frame (~1 giây) khi xe tạm thời bị che khuất
        - minimum_matching_threshold: Độ khớp IoU giữa các frame (0.8)
        - frame_rate: Chuẩn 30 FPS
        """
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate
        )
        print("ByteTrack Multi-Object Tracker đã sẵn sàng...")

    def update(self, detections_list):
        """
        Nhận vào danh sách phát hiện từ DETR:
        detections_list = [
            {'box': [x1, y1, x2, y2], 'class_name': 'car', 'score': 0.95, 'class_id': 2}, ...
        ]
        
        Trả về danh sách đối tượng bám đuôi ĐÃ CÓ tracker_id:
        [
            {'box': [x1, y1, x2, y2], 'tracker_id': 1, 'class_name': 'car', 'score': 0.95}, ...
        ]
        """
        if not detections_list:
            # Nếu frame này không phát hiện được gì, truyền Detections rỗng để ByteTrack cập nhật nội suy
            empty_det = sv.Detections.empty()
            tracked_objects = self.tracker.update_with_detections(empty_det)
            return []

        # 1. Chuyển đổi dữ liệu sang định dạng numpy cho supervision.Detections
        boxes = np.array([d['box'] for d in detections_list], dtype=float)
        scores = np.array([d['score'] for d in detections_list], dtype=float)
        class_ids = np.array([d.get('class_id', 0) for d in detections_list], dtype=int)
        
        # Lưu kèm tên lớp (class_name) vào metadata của supervision
        class_names = [d['class_name'] for d in detections_list]

        detections_sv = sv.Detections(
            xyxy=boxes,
            confidence=scores,
            class_id=class_ids,
            data={"class_name": np.array(class_names)}
        )

        # 2. Cập nhật ByteTrack: Tự động ghép nối liên khung hình & gán tracker_id
        tracked_objects = self.tracker.update_with_detections(detections_sv)

        # 3. Đóng gói kết quả đầu ra
        results = []
        if len(tracked_objects) > 0 and tracked_objects.tracker_id is not None:
            for xyxy, tr_id, cls_id, conf, cls_name in zip(
                tracked_objects.xyxy,
                tracked_objects.tracker_id,
                tracked_objects.class_id,
                tracked_objects.confidence,
                tracked_objects.data["class_name"]
            ):
                results.append({
                    "box": [round(float(coord), 2) for coord in xyxy],
                    "tracker_id": int(tr_id),
                    "class_name": str(cls_name),
                    "score": round(float(conf), 4),
                    "class_id": int(cls_id)
                })

        return results
