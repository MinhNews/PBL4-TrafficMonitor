import os
import sys
import cv2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from ultralytics import YOLO

video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
cap = cv2.VideoCapture(video_path)

# Đọc frame 30
cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
ret, frame = cap.read()
cap.release()

if ret:
    h, w = frame.shape[:2]
    model = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))
    results = model.predict(frame, conf=0.25, verbose=False)[0]

    vis = frame.copy()
    out_dir = os.path.join(BASE_DIR, "tools", "visualize_crops")
    os.makedirs(out_dir, exist_ok=True)

    idx = 0
    for box in results.boxes:
        cls_id = int(box.cls[0].item())
        cls_name = model.names[cls_id]
        conf = float(box.conf[0].item())
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy().tolist())

        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, f"{cls_name} {conf:.2f}", (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Cắt vùng đầu
        if cls_name == "person":
            cx = (x1 + x2) // 2
            hw = int((x2 - x1) * 0.55)
            head_crop = frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
            if head_crop.size > 0:
                cv2.imwrite(os.path.join(out_dir, f"person_{idx}_head.jpg"), head_crop)
                cv2.rectangle(vis, (max(0, cx - hw // 2), max(0, y1)), (min(w, cx + hw // 2), min(h, y1 + int((y2 - y1) * 0.28))), (0, 0, 255), 2)
            idx += 1

    cv2.imwrite(os.path.join(out_dir, "frame_30_annotated.jpg"), vis)
    print(f"Annotated frame saved to {out_dir}/frame_30_annotated.jpg")
