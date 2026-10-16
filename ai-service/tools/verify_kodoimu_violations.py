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

class MockBackend:
    def __init__(self):
        self.violations = []
    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))
        print(f"\n🚨🚨🚨 [BẮT ĐƯỢC VI PHẠM THÀNH CÔNG!] Loại: {v_type} | Loại xe: {vehicle_type} | Conf: {conf:.2f}")
    def send_traffic_flow(self, count, vehicle_type):
        pass

def verify_kodoimu():
    video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Khong the mo: {video_path}")
        return

    detector = YoloDetector()
    helmet_clf = HelmetClassifier()
    backend = MockBackend()
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend)

    # Đọc từ frame 400 đến 500 (nơi 2 người không đội mũ đi qua rõ nhất)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 380)
    frame_idx = 380

    out_frames_dir = os.path.join(BASE_DIR, "tools", "kodoimu_verified_frames")
    os.makedirs(out_frames_dir, exist_ok=True)

    print("\n--- BẮT ĐẦU CHẠY KIỂM TRA TỪ FRAME 380 ĐẾN 480 ---")
    while cap.isOpened() and frame_idx < 480:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        clean_frame = frame.copy()
        h, w = frame.shape[:2]
        stop_line_y = int(h * 0.70)

        detections = detector.detect(frame)
        entities = tracker_manager.update(detections, stop_line_y=stop_line_y)

        for entity in entities:
            # Nếu là person hoặc rider, trích xuất vùng đầu
            if entity.stable_class == "person" or entity.role == "rider":
                x1, y1, x2, y2 = map(int, entity.box)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.32)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                if head_crop.size > 0 and head_crop.shape[0] >= 20 and head_crop.shape[1] >= 20:
                    confirmed_no_h, conf = helmet_clf.update_and_check(entity.id, head_crop)
                    if confirmed_no_h:
                        violation_engine.process_helmet_result(entity, True, conf, clean_frame)

            # Duy trì chốt vi phạm không đội mũ (Latch)
            if entity.id in violation_engine.violating_helmets or (entity.moto_id is not None and entity.moto_id in violation_engine.violating_helmets):
                entity.violation_no_helmet = True
                entity.set_role("rider", moto_id=entity.moto_id)

            entity.render(frame)

        if frame_idx % 20 == 0:
            cv2.imwrite(os.path.join(out_frames_dir, f"frame_{frame_idx}_result.jpg"), frame)

    cap.release()
    print(f"\n--- KẾT QUẢ CUỐI CÙNG ---")
    print(f"Tổng số biên bản bắt được: {len(backend.violations)}")
    for v in backend.violations:
        print(f"  Biên bản: {v}")

if __name__ == "__main__":
    verify_kodoimu()
