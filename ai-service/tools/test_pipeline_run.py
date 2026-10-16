import os
import sys
import time
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
from services.mqtt_service import MqttTrafficLightService
from services.vit_worker import AsyncViTWorker

CROPS_DIR = os.path.join(BASE_DIR, "tools", "debug_head_crops")
os.makedirs(CROPS_DIR, exist_ok=True)

def test_full_pipeline():
    print("--- [TEST TÍCH HỢP] Chạy 200 frame thực tế từ traffic2.mp4 ---")
    video_path = os.path.join(BASE_DIR, "dataset", "traffic2.mp4")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Khong the mo video: {video_path}")
        return

    detector = YoloDetector()
    helmet_clf = HelmetClassifier()
    backend = BackendService()
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend)
    vit_worker = AsyncViTWorker(helmet_clf, violation_engine)

    saved_crops = 0
    frame_idx = 0
    crop_sizes = []

    t0 = time.time()
    while cap.isOpened() and frame_idx < 200:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        clean_frame = frame.copy()
        h, w = frame.shape[:2]
        stop_line_y = int(h * getattr(config, "STOP_LINE_RATIO", 0.65))

        detections = detector.detect(frame)
        entities = tracker_manager.update(detections, stop_line_y=stop_line_y)

        active_tr_ids = set()
        for entity in entities:
            active_tr_ids.add(entity.id)
            if entity.role == "vehicle":
                violation_engine.check_red_light_violation(entity, "GREEN", stop_line_y, clean_frame)
                violation_engine.check_traffic_flow(entity, stop_line_y)

            if entity.role == "rider" and entity.raw_class == "person":
                x1, y1, x2, y2 = map(int, entity.box)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                if head_crop.size > 0:
                    ch, cw = head_crop.shape[:2]
                    crop_sizes.append((cw, ch))
                    if saved_crops < 25 and ch >= 14 and cw >= 14:
                        cv2.imwrite(os.path.join(CROPS_DIR, f"head_crop_{entity.id}_{saved_crops}_{cw}x{ch}.jpg"), head_crop)
                        saved_crops += 1
                    if ch >= 14 and cw >= 14:
                        vit_worker.submit(entity, head_crop, clean_frame)

            entity.render(frame)

        if frame_idx % 30 == 0:
            vit_worker.cleanup_old_tracks(active_tr_ids)

    cap.release()
    vit_worker.stop()
    t1 = time.time()

    print(f"\n[HOAN THANH] Da xu ly xong {frame_idx} frame trong {t1-t0:.2f}s ({frame_idx/(t1-t0):.2f} FPS).")
    print(f"  - Tong so vung cat dau (head crops) thu thap: {len(crop_sizes)}")
    if crop_sizes:
        widths = [s[0] for s in crop_sizes]
        heights = [s[1] for s in crop_sizes]
        print(f"  - Kich thuoc crop: Rộng min={min(widths)}px, max={max(widths)}px | Cao min={min(heights)}px, max={max(heights)}px")
        print(f"  - Da luu {saved_crops} anh mau crop vao: {CROPS_DIR}")

if __name__ == "__main__":
    test_full_pipeline()
