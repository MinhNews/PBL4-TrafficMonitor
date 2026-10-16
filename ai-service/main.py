import os, sys, cv2, time, argparse
import numpy as np

# Thêm thư mục gốc ai-service vào path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

from detectors.yolo_detector import YoloDetector
from detectors.helmet_classifier import HelmetClassifier
from core.tracker_manager import TrafficTrackerManager
from core.violation_engine import ViolationEngine
from services.backend_service import BackendService
from services.mqtt_service import MqttTrafficLightService
from services.vit_worker import AsyncViTWorker
from services.stream_service import LiveStreamServer

def main():
    print("=" * 68)
    print("🚦 HỆ THỐNG GIÁM SÁT GIAO THÔNG THÔNG MINH (PBL4 - NHÓM 3) 🚦")
    print("   Kiến trúc: YOLO11n (Spatial) + ViT (Transformer) + ByteTrack")
    print("=" * 68)

    # 1. Khởi tạo các tham số dòng lệnh
    dataset_video = os.path.abspath(os.path.join(os.path.dirname(__file__), "dataset", "traffic2.mp4"))
    default_source = dataset_video if os.path.exists(dataset_video) else "0"

    parser = argparse.ArgumentParser(description="PBL4 Traffic Monitor AI")
    parser.add_argument("--source", default=default_source, help="Đường dẫn file video hoặc webcam index (mặc định: traffic2.mp4)")
    parser.add_argument("--no-gui", action="store_true", help="Chạy chế độ headless không mở cửa sổ OpenCV")
    parser.add_argument("--standalone", action="store_true", help="Chế độ test cá nhân tại nhà (không yêu cầu xe máy)")
    args, _ = parser.parse_known_args()

    source = int(args.source) if str(args.source).isdigit() else args.source

    # 2. Khởi tạo các Mô hình AI Cốt Lõi
    print("\n📦 [1/4] Khởi tạo các mô hình AI...")
    detector = YoloDetector()
    helmet_clf = HelmetClassifier()

    # 3. Khởi tạo các Dịch vụ Ngoại vi (Services)
    print("🌐 [2/4] Khởi tạo kết nối Backend Spring Boot & MQTT ESP32...")
    backend_service = BackendService()
    mqtt_service = MqttTrafficLightService().start()

    # 4. Khởi tạo Tầng Lõi Nghiệp vụ (Core Engine)
    print("⚙️  [3/4] Khởi tạo động cơ xử lý vết và bắt vi phạm...")
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend_service)
    vit_worker = AsyncViTWorker(helmet_clf, violation_engine)

    # 5. Khởi chạy Máy chủ phát luồng Web (Port 5000)
    print("📡 [4/4] Khởi chạy máy chủ phát luồng Live Stream...")
    stream_server = LiveStreamServer(mqtt_service, violation_engine).start()

    # =========================================================================
    # CHẾ ĐỘ TEST ẢNH TĨNH (.jpg, .png, .jpeg)
    # =========================================================================
    is_image = isinstance(source, str) and os.path.isfile(source) and source.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))
    if is_image:
        print(f"\n📸 [ẢNH TĨNH] Đang phân tích file ảnh: '{source}'...")
        frame = cv2.imread(source)
        if frame is None:
            print("❌ Không thể đọc file ảnh.")
            return

        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        clean_frame = frame.copy()
        h, w = frame.shape[:2]
        detections = detector.detect(frame)

        for obj in detections:
            if obj["class_name"] == "person":
                x1, y1, x2, y2 = map(int, obj["box"])
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                is_no_helmet, conf = helmet_clf.predict_head(head)

                if is_no_helmet:
                    print(f"🚨 Phát hiện vi phạm: KHÔNG ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"[KO MU] {int(conf * 100)}%", (x1, max(20, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    backend_service.send_violation(clean_frame, "NO_HELMET", "MOTORCYCLE", conf)
                else:
                    print(f"✅ Hợp lệ: CÓ ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")

        stream_server.update_frame(frame, fps=0)
        if not args.no_gui:
            cv2.imshow("PBL4 - Traffic Monitor AI", frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return

    # =========================================================================
    # CHẾ ĐỘ XỬ LÝ VIDEO / WEBCAM THỜI GIAN THỰC (30 FPS)
    # =========================================================================
    cap = cv2.VideoCapture(source)
    frame_idx = 0 # C1: Biến đếm frame tăng đơn điệu không bị reset
    fps_count = 0
    fps_display = 0
    start_time = time.time()

    print("\n" + "-" * 68)
    print("💡 HƯỚNG DẪN ĐIỀU KHIỂN BẰNG BÀN PHÍM:")
    print("   [r] Bật cưỡng bức Đèn ĐỎ (kiểm tra phạt vượt đèn đỏ)")
    print("   [y] Bật cưỡng bức Đèn VÀNG (giảm tốc)")
    print("   [g] Bật lại Đèn XANH (lưu thông bình thường)")
    print("   [q] Thoát chương trình")
    print("-" * 68 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Tự động tua lại video lặp tuần hoàn (Seamless Loop)
            if isinstance(source, str) and os.path.exists(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                tracker_manager.reset()
                violation_engine.reset()
                vit_worker.reset() # C2: Xóa sạch trạng thái ViT khi video tua lại loop
                continue
            print("Đã hết video hoặc không thể đọc camera.")
            break

        frame_idx += 1

        # Tối ưu kích thước hiển thị vừa vặn màn hình (chiều cao chuẩn 720px)
        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        # Lưu bản copy sạch (không nét vẽ) để gửi Backend làm bằng chứng vi phạm
        clean_frame = frame.copy()
        h, w = frame.shape[:2]
        stop_line_y = int(h * getattr(config, "STOP_LINE_RATIO", 0.65)) # D1: Dùng STOP_LINE_RATIO

        # 1. Phát hiện đối tượng (YOLO11n) & Cập nhật bám đuôi (ByteTrack)
        detections = detector.detect(frame)
        entities = tracker_manager.update(detections, stop_line_y=stop_line_y, is_standalone=args.standalone)

        # 2. Vẽ Vạch Dừng giao thông (Đỏ khi đèn Đỏ, Xanh khi đèn Xanh)
        current_light = mqtt_service.current_light
        line_color = (0, 0, 255) if current_light == "RED" else (0, 200, 0)
        cv2.line(frame, (0, stop_line_y), (w, stop_line_y), line_color, 2)
        cv2.putText(frame, "VACH DUNG", (10, stop_line_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, line_color, 1)

        active_tr_ids = set()

        # 3. Động cơ phân tích vi phạm cho từng phương tiện
        for entity in entities:
            active_tr_ids.add(entity.id)

            # A. KIỂM TRA LỖI VƯỢT ĐÈN ĐỎ & LƯU LƯỢNG XE (xe cơ giới hoặc rider)
            if entity.role in ["vehicle", "rider"]:
                violation_engine.check_red_light_violation(entity, current_light, stop_line_y, clean_frame)
                violation_engine.check_traffic_flow(entity, stop_line_y)

            # B. KIỂM TRA MŨ BẢO HIỂM (Người lái xe máy rider hoặc person trên đường)
            if entity.role == "rider" or (entity.stable_class == "person" and entity.role != "vehicle"):
                x1, y1, x2, y2 = map(int, entity.box)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.32)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                if head_crop.size > 0 and head_crop.shape[0] >= 18 and head_crop.shape[1] >= 18:
                    vit_worker.submit(entity, head_crop, clean_frame)

            # Cập nhật kết quả phân loại từ ViT
            is_no_h, h_conf, has_res = vit_worker.get_status(entity.id)
            if has_res:
                if is_no_h:
                    entity.violation_no_helmet = True
                    entity.helmet_conf = h_conf
                    entity.set_role("rider", moto_id=entity.moto_id)
                elif entity.id not in violation_engine.violating_helmets:
                    entity.violation_no_helmet = False

            # Khóa trạng thái vi phạm không đội mũ (Latch): giữ vững khung đỏ [KO MU] suốt vòng đời của xe
            if entity.id in violation_engine.violating_helmets or (entity.moto_id is not None and entity.moto_id in violation_engine.violating_helmets):
                entity.violation_no_helmet = True
                entity.set_role("rider", moto_id=entity.moto_id)

        # PHƯƠNG ÁN 2: Hợp nhất vi phạm Mũ bảo hiểm về Bounding Box xe máy duy nhất & triệt tiêu box con
        tracker_manager.unify_motorcycle_violations(entities, violation_engine)

        # C. TRỰC QUAN HÓA BOUNDING BOX (Vững chãi, 2px, nhãn badge nền màu, không nhấp nháy - B3 & Phương án 2)
        for entity in entities:
            entity.render(frame)



        # 4. Dọn dẹp bộ nhớ định kỳ bằng biến đếm đơn điệu frame_idx (C1)
        fps_count += 1
        if frame_idx % 30 == 0:
            vit_worker.cleanup_old_tracks(active_tr_ids)


        # 5. Tính toán và hiển thị HUD (FPS, Trạng thái đèn)
        if time.time() - start_time >= 1.0:
            fps_display = fps_count
            fps_count = 0
            start_time = time.time()

        status_color = (0, 0, 255) if current_light == "RED" else (0, 200, 0)
        cv2.circle(frame, (16, 20), 7, status_color, -1)
        cv2.circle(frame, (16, 20), 8, (255, 255, 255), 1)
        cv2.putText(frame, f"DEN: {current_light}  |  FPS: {fps_display}", (32, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # 6. Phát luồng ảnh sang Web qua Flask MJPEG
        stream_server.update_frame(frame, fps=fps_display)

        # 7. Hiển thị cửa sổ OpenCV nếu bật GUI
        if not args.no_gui:
            try:
                cv2.imshow("PBL4 - Traffic Monitor AI (YOLO11n + ViT Helmet)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    mqtt_service.set_manual_light("RED")
                elif key == ord('y'):
                    mqtt_service.set_manual_light("YELLOW")
                elif key == ord('g'):
                    mqtt_service.set_manual_light("GREEN")
                elif key == ord('a'):
                    mqtt_service.reset_to_auto()
            except Exception:
                time.sleep(0.02)
        else:
            time.sleep(0.025)

    # Dọn dẹp tài nguyên khi kết thúc
    print("\n🛑 Đang giải phóng tài nguyên hệ thống...")
    vit_worker.stop()
    mqtt_service.stop()
    cap.release()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    print("✅ Đã tắt hệ thống an toàn.")

if __name__ == "__main__":
    main()
