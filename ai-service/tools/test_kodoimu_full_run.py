import os
import sys
import time
import cv2
import numpy as np

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
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
from services.vit_worker import AsyncViTWorker

class MockBackend:
    def __init__(self):
        self.violations = []
        self.flows = []
    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))
        print(f"\n🚨 [BIÊN BẢN VI PHẠM THÀNH CÔNG] Loại: {v_type} | Loại xe: {vehicle_type} | Conf: {conf:.2f}")
        sys.stdout.flush()
    def send_traffic_flow(self, count, vehicle_type):
        self.flows.append((count, vehicle_type))

def run_test():
    video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Lỗi: Không tìm thấy file {video_path}")
        return

    detector = YoloDetector()
    helmet_clf = HelmetClassifier()
    backend = MockBackend()
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend)
    vit_worker = AsyncViTWorker(helmet_clf, violation_engine)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"🎬 Bắt đầu chạy toàn bộ video 'videokodoimu.mp4' ({total_frames} frames)...")
    sys.stdout.flush()

    frame_idx = 0
    t0 = time.time()

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

        active_tr_ids = set()
        for entity in entities:
            active_tr_ids.add(entity.id)

            # A. KIỂM TRA LƯU LƯỢNG & ĐÈN ĐỎ
            if entity.role in ["vehicle", "rider"]:
                violation_engine.check_traffic_flow(entity, stop_line_y)

            # B. KIỂM TRA MŨ BẢO HIỂM
            if entity.role == "rider" or (entity.stable_class == "person" and entity.role != "vehicle"):
                x1, y1, x2, y2 = map(int, entity.box)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.32)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                if head_crop.size > 0 and head_crop.shape[0] >= 18 and head_crop.shape[1] >= 18:
                    vit_worker.submit(entity, head_crop, clean_frame)

            # Cập nhật kết quả ViT
            is_no_h, h_conf, has_res = vit_worker.get_status(entity.id)
            if has_res and is_no_h:
                entity.violation_no_helmet = True
                entity.set_role("rider")

        if frame_idx % 30 == 0:
            vit_worker.cleanup_old_tracks(active_tr_ids)
            fps_current = frame_idx / max(0.1, time.time() - t0)
            print(f"  Frame {frame_idx}/{total_frames} ({frame_idx/total_frames*100:.1f}%) | FPS: {fps_current:.1f} | Vi phạm: {len(backend.violations)} | Lưu lượng: {len(backend.flows)}")
            sys.stdout.flush()

    cap.release()
    # Chờ hàng đợi ViT xử lý nốt
    time.sleep(1.0)
    vit_worker.stop()

    print("\n" + "=" * 60)
    print(f"🎉 HOÀN THÀNH TOÀN BỘ VIDEO 'videokodoimu.mp4' ({frame_idx} frame):")
    print(f"  - Tổng số vi phạm bắt được: {len(backend.violations)}")
    for v in backend.violations:
        print(f"    👉 {v[0]} ({v[1]}) - Độ tin cậy: {v[2]*100:.1f}%")
    print(f"  - Tổng lưu lượng xe đếm được: {len(backend.flows)}")
    print("=" * 60)
    sys.stdout.flush()

if __name__ == "__main__":
    run_test()
