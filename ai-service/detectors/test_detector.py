import os, sys, cv2, time, threading, queue
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
from trackers.byte_tracker import ByteTrackerManager
from detectors.helmet_classifier import HelmetClassifier
from detectors.violation_sender import (
    start_light_listener,
    send_violation_to_backend,
    check_red_light_violation,
    current_traffic_light
)
import detectors.violation_sender as vs

class AsyncViTWorker:
    """
    Luồng ngầm xử lý phân loại Mũ bảo hiểm (ViT):
    ViT chạy nền độc lập, KHÔNG BAO GIỜ làm gián đoạn hay giảm FPS của luồng video chính!
    """
    def __init__(self, helmet_clf):
        self.helmet_clf = helmet_clf
        self.queue = queue.Queue(maxsize=10)
        self.checked_tracks = {}      # {tr_id: is_violating}
        self.processing_tracks = set() # Các xe đang được tính toán ngầm
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def submit(self, tr_id, head_crop, full_frame):
        if tr_id in self.checked_tracks or tr_id in self.processing_tracks:
            return
        if not self.queue.full():
            self.processing_tracks.add(tr_id)
            self.queue.put_nowait((tr_id, head_crop.copy(), full_frame.copy()))

    def get_status(self, tr_id):
        return self.checked_tracks.get(tr_id, False)

    def _worker(self):
        while self.running:
            try:
                tr_id, head_crop, full_frame = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                # Phân tích vùng đầu với Vision Transformer (ViT)
                confirmed_no_helmet, h_conf = self.helmet_clf.update_and_check(tr_id, head_crop)
                self.checked_tracks[tr_id] = confirmed_no_helmet
                if confirmed_no_helmet:
                    print(f"🚨 [PHÁT HIỆN VI PHẠM] Xe #{tr_id} KHÔNG ĐỘI MŨ BẢO HIỂM! (Độ tin cậy: {int(h_conf*100)}%)")
                    send_violation_to_backend(full_frame, "NO_HELMET", "MOTORCYCLE", h_conf)
            except Exception as e:
                print(f"[ViT Worker Error] {e}")
            finally:
                if tr_id in self.processing_tracks:
                    self.processing_tracks.remove(tr_id)
                self.queue.task_done()

def main():
    print("=" * 65)
    print("🚦 HỆ THỐNG GIÁM SÁT GIAO THÔNG AI (PBL4 - NHÓM 3) 🚦")
    print("=" * 65)

    # 1. Khởi tạo Mô hình Nhận diện (Dual-Mode: YOLO11 hoặc Deformable DETR)
    backend = getattr(config, "DETECTOR_BACKEND", "yolo").lower()
    if backend == "yolo":
        from detectors.yolo_detector import YoloDetector
        yolo_model = getattr(config, "YOLO_MODEL_NAME", "yolo11n.pt")
        print(f"🚀 [CHẾ ĐỘ THỜI GIAN THỰC] Sử dụng: YOLO11 ({yolo_model})")
        print(f"   + Ưu điểm: Tốc độ cao ~30 FPS, Bounding Box bám dính tức thì!")
        detector = YoloDetector(model_name=yolo_model)
        mode_label = f"YOLO11 ({yolo_model})"
    else:
        from detectors.deformable_detr_detector import DeformableDetrDetector
        print(f"🏛️ [CHẾ ĐỘ HỌC THUẬT] Sử dụng: Deformable DETR (SenseTime)")
        print(f"   + Ưu điểm: Phục vụ báo cáo lý thuyết đồ án và nghiên cứu SOTA!")
        detector = DeformableDetrDetector()
        mode_label = "Deformable DETR"

    # 2. Khởi tạo ByteTrack và ViT Worker
    tracker = ByteTrackerManager()
    helmet_clf = HelmetClassifier()
    vit_worker = AsyncViTWorker(helmet_clf)

    # 3. Khởi chạy luồng ngầm lắng nghe đèn MQTT
    mqtt_client = start_light_listener()

    SOURCE = r"C:\Users\DELL\Downloads\traffic2.mp4"
    cap = cv2.VideoCapture(SOURCE)

    prev_positions = {} # Lưu tọa độ Y đáy xe: {tracker_id: bottom_y}

    fps_count = 0
    start_time = time.time()
    fps_display = 0

    print("\n💡 HƯỚNG DẪN ĐIỀU KHIỂN:")
    print("   + Bấm phím 'r': Bật/Tắt cưỡng bức Đèn ĐỎ (để test vượt đèn đỏ)")
    print("   + Bấm phím 'g': Bật lại Đèn XANH")
    print("   + Bấm phím 'q': Thoát chương trình\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            if isinstance(SOURCE, str) and os.path.exists(SOURCE):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            print("Đã hết video hoặc không thể đọc camera.")
            break

        # Tự động co tỷ lệ video độ phân giải cao về vừa vặn màn hình laptop (chiều cao 720px)
        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        h, w = frame.shape[:2]
        stop_line_y = int(h * 0.65) # Vạch dừng nằm ở 65% chiều cao khung hình

        # 4. Nhận diện xe với Detector đã chọn
        detections = detector.detect(frame)

        # 5. Cập nhật bám đuôi với ByteTrack
        tracked_objects = tracker.update(detections)

        # 6. Vẽ Vùng Vạch Dừng quy định (Stop Zone 50px)
        zone_color = (0, 0, 255) if vs.current_traffic_light == "RED" else (0, 255, 0)
        # Lớp phủ bán trong suốt thể hiện vùng cấm vượt
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, stop_line_y - 25), (w, stop_line_y + 25), zone_color, -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        cv2.line(frame, (0, stop_line_y), (w, stop_line_y), zone_color, 2)
        cv2.putText(
            frame, 
            f"VACH DUNG QUY DINH (STOP LINE Y={stop_line_y})", 
            (15, stop_line_y - 28), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone_color, 2
        )


        # 7. Duyệt qua từng đối tượng đang được theo dõi
        for obj in tracked_objects:
            x1, y1, x2, y2 = map(int, obj["box"])
            tr_id = obj["tracker_id"]
            cls_name = obj["class_name"]
            conf = obj["score"]
            curr_bottom_y = y2

            # A. KIỂM TRA LỖI VƯỢT ĐÈN ĐỎ
            is_violating_red_light = False
            if tr_id in prev_positions:
                prev_bottom_y = prev_positions[tr_id]
                is_violating_red_light = check_red_light_violation(
                    tr_id, prev_bottom_y, curr_bottom_y, frame, cls_name, conf, stop_line_y=stop_line_y
                )
            prev_positions[tr_id] = curr_bottom_y

            # B. KIỂM TRA MŨ BẢO HIỂM CHO XE MÁY / NGƯỜI
            is_violating_helmet = vit_worker.get_status(tr_id)
            if not is_violating_helmet and cls_name in ["person", "motorcycle"]:
                head_h = max(10, int((y2 - y1) * 0.35))
                head_crop = frame[max(0, y1):min(h, y1 + head_h), max(0, x1):min(w, x2)]
                
                # Gửi ảnh vùng đầu vào luồng ngầm ViT phân tích (không làm đứng video)
                if head_crop.size > 0 and head_crop.shape[0] >= 15 and head_crop.shape[1] >= 15:
                    vit_worker.submit(tr_id, head_crop, frame)

            # C. VẼ BOUNDING BOX VÀ NHÃN HIỂN THỊ
            if is_violating_red_light:
                box_color = (0, 0, 255) # Đỏ rực báo động vượt đèn đỏ
                label = f"[VUOT DEN DO] Xe #{tr_id}!"
            elif is_violating_helmet:
                box_color = (0, 0, 255) # Đỏ cảnh báo không đội mũ
                label = f"[KO DOI MU BH] Xe #{tr_id}"
            elif cls_name == "person":
                box_color = (0, 255, 255) # Vàng cho người
                label = f"Nguoi #{tr_id} {int(conf*100)}%"
            else:
                box_color = (255, 200, 0) # Xanh dương nhạt cho xe
                label = f"Xe #{tr_id} {cls_name} {int(conf*100)}%"

            # Vẽ khung viền xe
            box_thick = 3 if is_violating_red_light else 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, box_thick)

            # Vẽ nền chữ nổi (Text Badge) giúp chữ đọc cực rõ, không bị chìm vào mặt đường
            font_scale = 0.45
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            badge_y = max(th + 6, y1)
            cv2.rectangle(frame, (x1, badge_y - th - 5), (x1 + tw + 6, badge_y + 3), box_color, -1)
            text_color = (255, 255, 255) if (is_violating_red_light or is_violating_helmet) else (0, 0, 0)
            cv2.putText(frame, label, (x1 + 3, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1)

        # 8. Hiển thị thông tin hệ thống (FPS & Trạng thái đèn)
        fps_count += 1
        if time.time() - start_time >= 1.0:
            fps_display = fps_count
            fps_count = 0
            start_time = time.time()

        # Badge trạng thái đèn và mô hình đang dùng
        light_badge_color = (0, 0, 255) if vs.current_traffic_light == "RED" else (0, 255, 0)
        cv2.putText(frame, f"DEN: {vs.current_traffic_light}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, light_badge_color, 2)
        cv2.putText(frame, f"MODEL: {mode_label}", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 2)
        cv2.putText(frame, f"FPS: {fps_display}", (w - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Banner cảnh báo và thống kê vi phạm trên HUD
        total_viols = len(vs.violating_vehicles)
        viol_bg = (0, 0, 220) if total_viols > 0 else (40, 40, 40)
        cv2.rectangle(frame, (10, 85), (w - 10, 125), viol_bg, -1)
        cv2.rectangle(frame, (10, 85), (w - 10, 125), (255, 255, 255), 1)

        now_ts = time.time()
        active_viols = [t_id for t_id, t_time in vs.reported_violations.items() if now_ts - t_time < 4.0]
        if active_viols:
            banner_text = f"CANH BAO: XE #{active_viols[-1]} VUOT DEN DO!"
        else:
            banner_text = f"SO XE VUOT DEN DO: {total_viols}"
        cv2.putText(frame, banner_text, (15, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)

        cv2.imshow("PBL4 - Traffic Monitor AI (Dual-Mode: YOLO11 / Deformable DETR)", frame)




        # 9. Bắt phím điều khiển
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            vs.current_traffic_light = "RED"
            print("🚦 [THỦ CÔNG] Đã bật cưỡng bức ĐÈN ĐỎ!")
        elif key == ord('g'):
            vs.current_traffic_light = "GREEN"
            print("🚦 [THỦ CÔNG] Đã bật lại ĐÈN XANH!")

    vit_worker.running = False
    cap.release()
    cv2.destroyAllWindows()
    if mqtt_client:
        mqtt_client.loop_stop()

if __name__ == "__main__":
    main()
