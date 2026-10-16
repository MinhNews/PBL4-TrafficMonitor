import os
import sys
import cv2
import torch
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from ultralytics import YOLO
from detectors.helmet_classifier import HelmetClassifier

model = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))
clf = HelmetClassifier()

frame_path = os.path.join(BASE_DIR, "tools", "best_frame_445.jpg")
frame = cv2.imread(frame_path)
h, w = frame.shape[:2]

res = model.predict(frame, conf=0.25, verbose=False)[0]

vis = frame.copy()
out_dir = os.path.join(BASE_DIR, "tools", "frame_445_analysis")
os.makedirs(out_dir, exist_ok=True)

print(f"Phân tích Frame 445 (Kích thước: {w}x{h}):")
idx = 0
for box in res.boxes:
    cls_id = int(box.cls[0].item())
    cls_name = model.names[cls_id]
    conf = float(box.conf[0].item())
    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy().tolist())

    color = (0, 255, 0) if cls_name == "person" else (255, 0, 0)
    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
    cv2.putText(vis, f"{cls_name} {conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    print(f"  Object {idx}: {cls_name:12} | Conf: {conf:.2f} | BBox: [{x1}, {y1}, {x2}, {y2}] | Size: {x2-x1}x{y2-y1}")

    if cls_name == "person":
        cx = (x1 + x2) // 2
        hw = int((x2 - x1) * 0.55)
        head_crop = frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
        if head_crop.size > 0:
            ch, cw = head_crop.shape[:2]
            cv2.imwrite(os.path.join(out_dir, f"person_{idx}_head_{cw}x{ch}.jpg"), head_crop)
            is_no_h, p_conf = clf.predict_head(head_crop)
            print(f"    -> Head Crop: {cw}x{ch} px | ViT: is_no_helmet={is_no_h} (P_no_helmet={p_conf:.4f})")
    idx += 1

cv2.imwrite(os.path.join(out_dir, "frame_445_annotated.jpg"), vis)
print(f"Đã lưu kết quả trực quan vào: {out_dir}/frame_445_annotated.jpg")
