import os
import sys
import cv2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from ultralytics import YOLO

video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
cap = cv2.VideoCapture(video_path)
model = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))

frame_idx = 0
found_moments = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1

    if frame_idx % 10 == 0:
        res = model.predict(frame, conf=0.25, verbose=False)[0]
        # Tìm các person hoặc motorcycle ở bên phải (x > 500)
        right_persons = []
        right_motos = []
        for box in res.boxes:
            cname = model.names[int(box.cls[0].item())]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
            if x1 > 450:
                if cname == "person":
                    right_persons.append((x1, y1, x2, y2))
                elif cname == "motorcycle":
                    right_motos.append((x1, y1, x2, y2))

        if len(right_persons) > 0:
            found_moments.append((frame_idx, len(right_persons), len(right_motos)))

cap.release()

print(f"Tổng số frame quét: {frame_idx}")
print(f"Các frame phát hiện người đi xe máy bên phải ({len(found_moments)} frame):")
for f_idx, np_cnt, nm_cnt in found_moments[:20]:
    print(f"  Frame {f_idx}: {np_cnt} person, {nm_cnt} moto")
if len(found_moments) > 20:
    print(f"  ... và {len(found_moments)-20} frame tiếp theo.")
