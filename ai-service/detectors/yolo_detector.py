import cv2
import numpy as np
from ultralytics import YOLO
import sys, os

# Thêm thư mục cha vào đường dẫn để import config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

class YoloDetector:
    """
    Module nhận diện phương tiện thời gian thực sử dụng YOLO11 (Ultralytics).
    Đảm bảo 100% chuẩn giao tiếp với ByteTrack và toàn bộ hệ thống PBL4:
    Trả về danh sách: [
        {'box': [x1, y1, x2, y2], 'class_name': 'car', 'score': 0.88, 'class_id': 2}, ...
    ]
    """
    def __init__(self, model_name=None, conf_threshold=None, imgsz=416):
        self.model_name = model_name or getattr(config, "YOLO_MODEL_NAME", "yolo11n.pt")
        self.conf_threshold = conf_threshold or getattr(config, "DETR_CONFIDENCE_THRESHOLD", 0.35)
        self.imgsz = imgsz
        print(f"[YOLO] Dang nap mo hinh: {self.model_name} (imgsz={self.imgsz}, conf={self.conf_threshold})...")
        self.model = YOLO(self.model_name)

        # Chạy khởi động (Warmup) để triệt tiêu độ trễ compile ở frame đầu tiên
        dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        _ = self.model.predict(dummy, imgsz=self.imgsz, verbose=False)
        print(f"[YOLO] Mo hinh {self.model_name} da san sang!")


    def detect(self, frame_bgr):
        """
        Nhận vào 1 frame hình từ OpenCV (BGR)
        Trả về danh sách đối tượng thuộc TARGET_CLASSES:
        car, motorcycle, bus, truck, bicycle, person
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        # Chạy dự đoán với YOLO
        results = self.model.predict(
            frame_bgr,
            conf=self.conf_threshold,
            imgsz=self.imgsz,
            verbose=False
        )[0]

        detections = []
        if results.boxes is not None and len(results.boxes) > 0:
            boxes = results.boxes.xyxy.cpu().numpy()
            scores = results.boxes.conf.cpu().numpy()
            class_ids = results.boxes.cls.cpu().numpy().astype(int)

            for box, score, cls_id in zip(boxes, scores, class_ids):
                class_name = self.model.names.get(cls_id, "").lower()

                # Lọc đúng các lớp giao thông quan tâm (Task 2.1)
                if class_name in config.TARGET_CLASSES:
                    detections.append({
                        "box": [round(float(coord), 2) for coord in box],
                        "class_name": class_name,
                        "score": round(float(score), 4),
                        "class_id": int(cls_id)
                    })

        return detections
