import os
import sys
import cv2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

video_path = os.path.join(BASE_DIR, "dataset", "videokodoimu.mp4")
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Cannot open {video_path}")
    sys.exit(1)

w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / max(1.0, fps)

print(f"Video: {video_path}")
print(f"Resolution: {w}x{h}")
print(f"FPS: {fps:.2f}")
print(f"Total Frames: {total_frames}")
print(f"Duration: {duration:.2f} seconds")

# Save a few keyframes to inspect
output_dir = os.path.join(BASE_DIR, "tools", "inspect_kodoimu")
os.makedirs(output_dir, exist_ok=True)

frame_indices = [0, total_frames // 4, total_frames // 2, 3 * total_frames // 4, total_frames - 1]
for idx in frame_indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(os.path.join(output_dir, f"frame_{idx}.jpg"), frame)

cap.release()
print(f"Saved keyframes to: {output_dir}")
