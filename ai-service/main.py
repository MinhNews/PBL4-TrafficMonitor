import os, sys, cv2, time, argparse
import numpy as np

# Thêm thư mục gốc ai-service vào path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config
import runtime_config

from detectors.yolo_detector import YoloDetector
from detectors.helmet_classifier import HelmetClassifier
from core.camera_manager import CameraManager
from core.tracker_manager import TrafficTrackerManager
from core.violation_engine import ViolationEngine
from services.backend_service import BackendService
from services.mqtt_service import MqttTrafficLightService
from services.vit_worker import AsyncViTWorker
from services.stream_service import LiveStreamServer

def main():
    print("=" * 68)
    print("🚦 HỆ THỐNG GIÁM SÁT GIAO THÔNG THÔNG MINH (PBL4 - NHÓM 3) 🚦")
    print(f"   Kiến trúc: {config.YOLO_MODEL_NAME} (Spatial) + ViT (Transformer) + ByteTrack")
    print("=" * 68)

    # 1. Khởi tạo các tham số dòng lệnh
    parser = argparse.ArgumentParser(description="PBL4 Traffic Monitor AI")
    parser.add_argument("--source", default=None,
                        help="Chạy 1 nguồn duy nhất (ghi đè danh sách camera trong config.py) — dùng để test nhanh")
    parser.add_argument("--camera", type=int, default=None,
                        help="ID camera khởi động (mặc định: config.DEFAULT_CAMERA_ID)")
    parser.add_argument("--no-gui", action="store_true", help="Chạy chế độ headless không mở cửa sổ OpenCV")
    parser.add_argument("--standalone", action="store_true", help="Chế độ test cá nhân tại nhà (không yêu cầu xe máy)")
    args, _ = parser.parse_known_args()

    # C4: nguồn camera — mặc định lấy danh sách trong config.py, đổi camera trên Web không cần restart
    if args.source:
        cameras = [{
            "id": getattr(config, "CAMERA_ID", 1),
            "name": "Nguồn tùy chọn (--source)",
            "source": args.source,
        }]
        initial_camera_id = cameras[0]["id"]
        print(f"📷 [CAMERA] Chế độ 1 nguồn (--source): {args.source}")
    else:
        cameras = getattr(config, "CAMERAS", [])
        initial_camera_id = args.camera or getattr(config, "DEFAULT_CAMERA_ID", 1)

    camera_manager = CameraManager(cameras=cameras, initial_id=initial_camera_id)
    source = camera_manager.active_source()

    # 2. Khởi tạo các Mô hình AI Cốt Lõi
    print("\n📦 [1/4] Khởi tạo các mô hình AI...")
    detector = YoloDetector()
    helmet_clf = HelmetClassifier()

    # 3. Khởi tạo các Dịch vụ Ngoại vi (Services)
    print("🌐 [2/4] Khởi tạo kết nối Backend Spring Boot & MQTT ESP32...")
    backend_service = BackendService()
    backend_service.set_camera_id(camera_manager.active_id())
    mqtt_service = MqttTrafficLightService().start()

    # 4. Khởi tạo Tầng Lõi Nghiệp vụ (Core Engine)
    print("⚙️  [3/4] Khởi tạo động cơ xử lý vết và bắt vi phạm...")
    runtime_config.load()  # C2: nạp vạch dừng / chiều xe đã chỉnh từ Web (nếu có)
    tracker_manager = TrafficTrackerManager()
    violation_engine = ViolationEngine(backend_service)
    violation_engine.approach_direction = runtime_config.approach_direction()
    vit_worker = AsyncViTWorker(helmet_clf, violation_engine)

    # 5. Khởi chạy Máy chủ phát luồng Web (Port 5000)
    print("📡 [4/4] Khởi chạy máy chủ phát luồng Live Stream...")
    stream_server = LiveStreamServer(mqtt_service, violation_engine, camera_manager=camera_manager).start()

    # =========================================================================
    # CHẾ ĐỘ TEST ẢNH TĨNH (.jpg, .png, .jpeg)
    # =========================================================================
    is_image = camera_manager.active_is_image()
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
    cap = camera_manager.open_active_capture()
    if cap is None:
        print(f"❌ Không mở được camera: {camera_manager.active_name()} ({source})")
        mqtt_service.stop()
        return

    frame_idx = 0 # C1: Biến đếm frame tăng đơn điệu không bị reset
    fps_count = 0
    fps_display = 0
    start_time = time.time()

    def reset_session(reason):
        """C4: đổi camera / video lặp lại -> xoá sạch trạng thái bám đuôi của phiên cũ."""
        nonlocal fps_count, fps_display, start_time
        tracker_manager.reset()
        violation_engine.reset()
        vit_worker.reset()
        fps_count = 0
        fps_display = 0
        start_time = time.time()
        print(f"🔄 [PHIÊN MỚI] {reason}")

    print("\n" + "-" * 68)
    print("💡 HƯỚNG DẪN ĐIỀU KHIỂN:")
    print("   [r] Bật cưỡng bức Đèn ĐỎ (kiểm tra phạt vượt đèn đỏ)")
    print("   [y] Bật cưỡng bức Đèn VÀNG (giảm tốc)")
    print("   [g] Bật lại Đèn XANH (lưu thông bình thường)")
    print("   [q] Thoát chương trình")
    print("   🎥 Đổi camera trên Web (Live Camera) — không cần restart AI")
    cam = camera_manager.active_camera()
    print(f"   Đang giám sát: {cam['name']} (id={cam['id']})")
    print("-" * 68 + "\n")

    while True:
        # 0. C4: áp dụng yêu cầu đổi camera giữa hai frame (không tranh chấp với YOLO/ByteTrack)
        pending_id = camera_manager.take_pending()
        if pending_id is not None:
            new_cap = camera_manager.open_capture(pending_id)
            if new_cap is None:
                print(f"❌ [CAMERA] Không mở được camera id={pending_id}, giữ nguyên camera hiện tại.")
            else:
                camera_manager.set_active(pending_id)
                backend_service.set_camera_id(pending_id)
                reset_session(f"Chuyển sang {camera_manager.active_name()}")
                cap = new_cap
                print(f"🎥 [CAMERA] Đang giám sát: {camera_manager.active_name()}")
            continue

        ret, frame = cap.read()
        if not ret:
            # Tự động tua lại video lặp tuần hoàn (Seamless Loop)
            if camera_manager.active_is_looping():
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                reset_session("Video lặp lại từ đầu")
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
        # C2: Tỉ lệ vạch dừng đọc từ runtime_config -> chỉnh được trên Web, không cần restart
        stop_line_y = int(h * runtime_config.stop_line_ratio())

        # 1. Phát hiện đối tượng (YOLO11n) & Cập nhật bám đuôi (ByteTrack)
        detections = detector.detect(frame)
        entities = tracker_manager.update(detections, stop_line_y=stop_line_y, is_standalone=args.standalone)

        # 2. Vẽ Vạch Dừng giao thông (Đỏ khi đèn Đỏ, Xanh khi đèn Xanh)
        # C4: nút bật/tắt chỉ ảnh hưởng phần VẼ; logic stop_line_y bên dưới giữ nguyên
        current_light = mqtt_service.current_light
        if runtime_config.stop_line_visible():
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
                    vit_worker.submit(entity, head_crop, clean_frame, camera_manager.active_id())

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
            # B1: Dọn bộ nhớ vi phạm/lưu lượng của các xe đã khuất khỏi khung hình.
            # Chạy camera thật nhiều giờ mà không có bước này thì dict sẽ phình vô hạn.
            violation_engine.prune_stale()


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
                cv2.imshow(f"PBL4 - Traffic Monitor AI ({config.YOLO_MODEL_NAME} + ViT Helmet)", frame)
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
    camera_manager.release_all()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    print("✅ Đã tắt hệ thống an toàn.")

if __name__ == "__main__":
    main()
