import cv2
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from detectors.yolo_detector import YoloDetector
from core.tracker_manager import TrafficTrackerManager

def inspect_kodoimu_tracks():
    video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 415)
    
    detector = YoloDetector(model_name="yolo11s.pt")
    tracker_manager = TrafficTrackerManager()
    
    for f in range(415, 435):
        ret, frame = cap.read()
        if not ret: break
        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))
        h, w = frame.shape[:2]
        stop_line_y = int(h * 0.65)
        dets = detector.detect(frame)
        entities = tracker_manager.update(dets, stop_line_y=stop_line_y)
        
        # Look for entities in x: [650, 850] and y: [150, 450]
        on_bike = [e for e in entities if e.box[0] > 650 and e.box[1] < 450]
        print(f"F{f}: {[f'ID #{e.id} ({e.stable_class},{e.role},moto_id={e.moto_id},box={[int(c) for c in e.box]})' for e in on_bike]}")

    cap.release()

if __name__ == "__main__":
    inspect_kodoimu_tracks()
