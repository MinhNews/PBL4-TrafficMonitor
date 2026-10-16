import cv2
import os
import sys
from ultralytics import YOLO

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

def inspect_traffic2_yolo():
    video_path = os.path.join(BASE_DIR, "dataset", "traffic2.mp4")
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("Cannot read traffic2.mp4")
        return

    if frame.shape[0] > 720:
        scale = 720 / frame.shape[0]
        frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

    model = YOLO("yolo11n.pt")
    
    for conf in [0.25, 0.15, 0.10]:
        print(f"\n--- Testing YOLO conf = {conf} ---")
        results = model(frame, conf=conf, iou=0.6, verbose=False)[0]
        for box, cls_id, score in zip(results.boxes.xyxy.cpu().numpy(), results.boxes.cls.cpu().numpy(), results.boxes.conf.cpu().numpy()):
            cls_name = model.names[int(cls_id)]
            if cls_name in ["person", "motorcycle", "bicycle", "car", "truck", "bus"]:
                print(f"  {cls_name} ({score:.2f}): box={[int(c) for c in box]}")

if __name__ == "__main__":
    inspect_traffic2_yolo()
