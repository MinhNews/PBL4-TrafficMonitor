import os
import sys
import cv2
import torch
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from ultralytics import YOLO
from detectors.helmet_classifier import HelmetClassifier

video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
cap = cv2.VideoCapture(video_path)
model = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))
clf = HelmetClassifier()

out_dir = os.path.join(BASE_DIR, "tools", "test_riders_heads")
os.makedirs(out_dir, exist_ok=True)

test_frames = [20, 40, 60, 80, 100, 120, 140, 160]

print("\n--- TEST CHI TIẾT CÁC BBOX PERSON TRÊN TỪNG FRAME ---")
for f_idx in test_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
    ret, frame = cap.read()
    if not ret:
        continue
    h, w = frame.shape[:2]
    res = model.predict(frame, conf=0.25, verbose=False)[0]

    p_idx = 0
    for box in res.boxes:
        cname = model.names[int(box.cls[0].item())]
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy().tolist())
        # Chỉ xét các person ở bên phải (vùng 2 người đi xe máy không mũ)
        if cname == "person" and x1 > 450:
            cx = (x1 + x2) // 2
            hw = int((x2 - x1) * 0.6)
            head_crop = frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.35)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
            if head_crop.size > 0:
                ch, cw = head_crop.shape[:2]
                rgb = cv2.cvtColor(head_crop, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                inputs = clf.processor(images=pil_img, return_tensors="pt").to(clf.device)
                with torch.no_grad():
                    logits = clf.model(**inputs).logits
                    probs = torch.softmax(logits, dim=-1)[0]
                    p_no_helmet = float(probs[clf.no_helmet_idx].item())
                    p_helmet = float(probs[0].item())

                img_name = f"f{f_idx}_p{p_idx}_noH_{p_no_helmet:.2f}_H_{p_helmet:.2f}_{cw}x{ch}.jpg"
                cv2.imwrite(os.path.join(out_dir, img_name), head_crop)
                print(f"Frame {f_idx} | Person {p_idx} (box {x1},{y1} {x2-x1}x{y2-y1}) | Head {cw}x{ch} | P(no_helmet)={p_no_helmet:.3f} | P(helmet)={p_helmet:.3f}")
                p_idx += 1

cap.release()
print(f"Đã lưu ảnh các vùng đầu vào: {out_dir}")
