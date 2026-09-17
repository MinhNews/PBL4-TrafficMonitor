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
    # - 0: Webcam máy tính
    # - "traffic.mp4": File Video
    # - "img1.jpg": File Ảnh đơn
    SOURCE = "img1.jpg"  # Đổi nguồn tại đây: 0, "traffic.mp4", hoặc "img1.jpg"

    detector = DeformableDetrDetector()

    # KHỐI 1: XỬ LÝ NẾU NGUỒN ĐẦU VÀO LÀ 1 BỨC ẢNH (.jpg, .png, .jpeg)
    if isinstance(SOURCE, str) and SOURCE.lower().endswith(('.jpg', '.jpeg', '.png')):
        print(f"🖼️ Đang quét bức ảnh: {SOURCE}...")
        if not os.path.exists(SOURCE):
            print(f"❌ Lỗi: Không tìm thấy tệp ảnh '{SOURCE}'.")
            return

        frame = cv2.imread(SOURCE)
        start_t = time.time()
        detections = detector.detect(frame)
        infer_time = (time.time() - start_t) * 1000

        print(f"✅ Đã tìm thấy {len(detections)} đối tượng trong {infer_time:.1f}ms:")

        for d in detections:
            x1, y1, x2, y2 = map(int, d["box"])
            label = f"{d['class_name']}: {int(d['score']*100)}%"
            print(f"   + Lớp: {d['class_name']} ({int(d['score']*100)}%) | BBox: [{x1}, {y1}, {x2}, {y2}]")

            # Xanh lá cho phương tiện, Vàng cho người đi bộ
            color = (0, 255, 0) if d["class_name"] != "person" else (0, 255, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        output_img = "detr_result.jpg"
        cv2.imwrite(output_img, frame)
        print(f"💾 Đã lưu ảnh kết quả nhận diện vào: {os.path.abspath(output_img)}")

        cv2.imshow("Deformable DETR - PBL4 Traffic Monitor (Image Test)", frame)
        print("💡 Bấm phím bất kỳ trên cửa sổ ảnh để đóng...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # KHỐI 2: XỬ LÝ NẾU NGUỒN ĐẦU VÀO LÀ WEBCAM HOẶC VIDEO (.mp4)
    cap = cv2.VideoCapture(SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    print("🚀 Bắt đầu nhận diện Video/Webcam! Bấm phím 'q' để dừng...")

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

        if frame_idx % config.PROCESS_EVERY_N_FRAMES == 0:
            last_detections = detector.detect(frame)

        for d in last_detections:
            x1, y1, x2, y2 = map(int, d["box"])
            label = f"{d['class_name']}: {int(d['score']*100)}%"
            color = (0, 255, 0) if d["class_name"] != "person" else (0, 255, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        fps_count += 1
        if time.time() - start_time >= 1.0:
            fps_display = fps_count
            fps_count = 0
            start_time = time.time()

        cv2.putText(frame, f"FPS: {fps_display}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imshow("Deformable DETR - PBL4 Traffic Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
