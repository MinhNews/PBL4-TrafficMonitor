"""
Chạy file này để test nhận diện Deformable DETR:
python detectors/test_detector.py
"""
import cv2
import time
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from detectors.deformable_detr_detector import DeformableDetrDetector
import config

def main():
    # CHỌN NGUỒN ĐẦU VÀO:
    # - Số 0: Mở Webcam máy tính
    # - "traffic.mp4": Mở file video giao thông có sẵn trong thư mục
    SOURCE = config.WEBCAM_INDEX # Hoặc thay bằng "traffic.mp4"

    detector = DeformableDetrDetector()
    cap = cv2.VideoCapture(SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    print("🚀 Bắt đầu nhận diện! Bấm phím 'q' trên cửa sổ video để dừng...")

    fps_count = 0
    start_time = time.time()
    fps_display = 0
    frame_idx = 0
    last_detections = []

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Đã hết video hoặc không thể đọc từ camera.")
            break

        frame_idx += 1

        # TỐI ƯU HIỆU NĂNG: Chỉ chạy model DETR mỗi 3 frame (Frame Skipping)
        # Các frame ở giữa sử dụng lại kết quả box trước đó để đạt FPS cao mượt mà
        if frame_idx % config.PROCESS_EVERY_N_FRAMES == 0:
            last_detections = detector.detect(frame)

        # Vẽ Bounding Box lên khung hình
        for d in last_detections:
            x1, y1, x2, y2 = map(int, d["box"])
            label = f"{d['class_name']}: {int(d['score']*100)}%"

            # Xanh lá cho phương tiện, Vàng cho người đi bộ
            color = (0, 255, 0) if d["class_name"] != "person" else (0, 255, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Tính toán và hiển thị tốc độ khung hình (FPS)
        fps_count += 1
        if time.time() - start_time >= 1.0:
            fps_display = fps_count
            fps_count = 0
            start_time = time.time()

        cv2.putText(frame, f"FPS: {fps_display}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imshow("Deformable DETR - PBL4 Traffic Monitor", frame)

        if cv2.waitkey(1) & 0xFF == ord('q') if hasattr(cv2, 'waitkey') else cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
