import os
import sys
import cv2
import numpy as np

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

import config
from detectors.yolo_detector import YoloDetector
from detectors.helmet_classifier import HelmetClassifier
from core.tracker_manager import TrafficTrackerManager
from core.violation_engine import ViolationEngine
from services.backend_service import BackendService

class MockBackend:
    def __init__(self):
        self.violations = []
    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))
        print(f"  >>> [GỬI BIÊN BẢN] Loại: {v_type} | Loại xe: {vehicle_type} | Conf: {conf:.2f}")
    def send_traffic_flow(self, count, vehicle_type):
        pass

def run_test_kodoimu():
    video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Khong mo duoc: {video_path}")
        return

    detector = YoloDetector()
    helmet_clf = HelmetClassifier()
    backend = MockBackend()
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend)

    crops_dir = os.path.join(BASE_DIR, "tools", "inspect_kodoimu_crops")
    os.makedirs(crops_dir, exist_ok=True)

    frame_idx = 0
    saved_crops = 0

    print("\n--- BẮT ĐẦU CHẠY PHÂN TÍCH 'videokodoimu.mp4' ---")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        clean_frame = frame.copy()
        h, w = frame.shape[:2]
        stop_line_y = int(h * getattr(config, "STOP_LINE_RATIO", 0.65))

        detections = detector.detect(frame)
        entities = tracker_manager.update(detections, stop_line_y=stop_line_y)

        for entity in entities:
            # Kiểm tra crop đầu cho mọi person hoặc rider
            # (Thử nghiệm để xem ViT phán đoán thế nào với 2 người đi xe máy không mũ)
            x1, y1, x2, y2 = map(int, entity.box)
            cx = (x1 + x2) // 2
            hw = int((x2 - x1) * 0.55)
            head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]

            if head_crop.size > 0:
                ch, cw = head_crop.shape[:2]
                is_no_h, conf = helmet_clf.predict_head(head_crop)
                
                # Lưu một số crop đầu đặc trưng để kiểm tra bằng mắt
                if frame_idx % 15 == 0 and saved_crops < 30 and cw >= 12 and ch >= 12:
                    label_str = "no_helmet" if is_no_h else "helmet"
                    crop_filename = f"crop_f{frame_idx}_id{entity.id}_{entity.role}_{label_str}_{conf:.2f}_{cw}x{ch}.jpg"
                    cv2.imwrite(os.path.join(crops_dir, crop_filename), head_crop)
                    saved_crops += 1

                # Nếu là rider, cập nhật qua ViT history
                if entity.role == "rider" or (entity.stable_class == "person" and abs(entity.velocity_y) > 0.5):
                    confirmed_no_h, h_conf = helmet_clf.update_and_check(entity.id, head_crop)
                    if confirmed_no_h:
                        violation_engine.process_helmet_result(entity, True, h_conf, clean_frame)

    cap.release()
    print(f"\n--- KẾT THÚC PHÂN TÍCH ({frame_idx} frame) ---")
    print(f"Tổng số biên bản đã gửi: {len(backend.violations)}")
    for v in backend.violations:
        print(f"  Biên bản: {v}")
    print(f"Đã lưu {saved_crops} ảnh crop đầu vào: {crops_dir}")

if __name__ == "__main__":
    run_test_kodoimu()
