import os
import sys
import cv2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from ultralytics import YOLO

video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
cap = cv2.VideoCapture(video_path)
model = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))

max_area = 0
best_frame_idx = 0
best_boxes = []

frame_idx = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    if frame_idx % 5 == 0:
        res = model.predict(frame, conf=0.25, verbose=False)[0]
        for box in res.boxes:
            cname = model.names[int(box.cls[0].item())]
            if cname in ["person", "motorcycle"]:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
                area = (x2 - x1) * (y2 - y1)
                if x1 > 400 and area > max_area:
                    max_area = area
                    best_frame_idx = frame_idx
                    best_boxes = [(cname, x1, y1, x2, y2)]

cap.release()
print(f"Frame với đối tượng xe/người lớn nhất ở làn phải: Frame {best_frame_idx} (Diện tích: {max_area:.0f} px^2)")

# Lưu frame đó ra ảnh
cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, best_frame_idx)
ret, frame = cap.read()
if ret:
    cv2.imwrite(os.path.join(BASE_DIR, "tools", f"best_frame_{best_frame_idx}.jpg"), frame)
    print(f"Đã lưu frame lớn nhất vào: tools/best_frame_{best_frame_idx}.jpg")
cap.release()
