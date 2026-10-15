import os, sys, cv2, time, threading, queue
import numpy as np
from flask import Flask, Response, jsonify, request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config
from trackers.byte_tracker import ByteTrackerManager
from detectors.helmet_classifier import HelmetClassifier
from detectors.violation_sender import (
    start_light_listener,
    send_violation_to_backend,
    check_red_light_violation,
    check_traffic_flow,
    current_traffic_light
)
import detectors.violation_sender as vs

# Flask MJPEG Live Streaming Server (Port 5000)
flask_app = Flask(__name__)
latest_jpeg = None
frame_lock = threading.Lock()
stream_metrics = {"fps": 0, "status": "ONLINE"}

@flask_app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response

@flask_app.route('/health')
@flask_app.route('/status')
def status():
    w = stream_metrics.get("width", 0)
    h = stream_metrics.get("height", 0)
    esp32_active = vs.is_esp32_online()
    return jsonify({
        "status": "ONLINE",
        "fps": stream_metrics["fps"],
        "light": vs.current_traffic_light,
        "esp32Online": esp32_active,
        "remainingSeconds": vs.esp32_remaining_seconds if esp32_active else None,
        "mode": "ESP32_HARDWARE" if esp32_active else "TEST_STANDALONE",
        "vehiclesPassed": len(vs.passed_vehicles),
        "violations": len(vs.violating_vehicles),
        "width": w,
        "height": h,
        "orientation": "PORTRAIT" if h > w else "LANDSCAPE",
        "timestamp": time.time()
    })

@flask_app.route('/light', methods=['POST'])
def set_light():
    if vs.is_esp32_online():
        return jsonify({
            "error": "ESP32_LOCKED",
            "message": "Hệ thống khóa can thiệp thủ công để đảm bảo tính xác thực.",
            "light": vs.current_traffic_light,
            "esp32Online": True
        }), 403

    data = request.get_json(silent=True) or {}
    new_light = data.get("light", "").upper()
    if new_light in ["RED", "GREEN", "YELLOW"]:
        vs.set_manual_light(new_light)
    return jsonify({
        "light": vs.current_traffic_light,
        "esp32Online": False,
        "mode": "TEST_STANDALONE"
    })

@flask_app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with frame_lock:
                frame_bytes = latest_jpeg
            if frame_bytes is None:
                time.sleep(0.04)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start_flask_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    flask_app.run(host='0.0.0.0', port=5000, threaded=True, debug=False, use_reloader=False)

class AsyncViTWorker:
    """
    Luồng ngầm xử lý phân loại Mũ bảo hiểm (ViT):
    Đánh giá liên tục theo thời gian thực (real-time reactive), tự động chuyển đổi giữa [CO MU] và [KO MU].
    """
    def __init__(self, helmet_clf):
        self.helmet_clf = helmet_clf
        self.queue = queue.Queue(maxsize=20)
        self.track_status = {}         # {tr_id: {"is_no_helmet": bool, "conf": float}}
        self.reported_violations = {}  # {entity_key: timestamp} - Cooldown 30s chống báo lặp liên tục
        self.processing_tracks = set()
        self.last_checked = {}         # {tr_id: timestamp}
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def submit(self, tr_id, head_crop, clean_frame, moto_id=None, box=None):
        now = time.time()
        # Throttle: chỉ submit lại mỗi 0.12s để bắt kịp xe di chuyển nhanh
        if tr_id in self.processing_tracks or (now - self.last_checked.get(tr_id, 0)) < 0.12:
            return
        if not self.queue.full():
            self.processing_tracks.add(tr_id)
            self.last_checked[tr_id] = now
            self.queue.put_nowait((tr_id, head_crop.copy(), clean_frame, moto_id, box))

    def get_status(self, tr_id):
        # Trả về: (is_no_helmet: bool, conf: float, has_result: bool)
        if tr_id in self.track_status:
            info = self.track_status[tr_id]
            return info["is_no_helmet"], info["conf"], True
        return False, 0.0, False

    def cleanup_old_tracks(self, active_tr_ids):
        now = time.time()
        expired = [tid for tid, ts in self.last_checked.items() if tid not in active_tr_ids and (now - ts) > 5.0]
        for tid in expired:
            self.track_status.pop(tid, None)
            self.last_checked.pop(tid, None)

        # Dọn dẹp bộ đếm frame trong classifier
        self.helmet_clf.cleanup_history(active_tr_ids)

        # Dọn dẹp cooldown vi phạm đã hết hạn sau 60 giây
        stale_entities = [k for k, ts in self.reported_violations.items() if (now - ts) > 60.0]
        for k in stale_entities:
            self.reported_violations.pop(k, None)

    def _worker(self):
        while self.running:
            try:
                tr_id, head_crop, clean_frame, moto_id, box = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                # Phân tích vùng đầu với Vision Transformer (ViT)
                confirmed_no_helmet, h_conf = self.helmet_clf.update_and_check(tr_id, head_crop)
                self.track_status[tr_id] = {"is_no_helmet": confirmed_no_helmet, "conf": h_conf}

                entity_key = f"moto_{moto_id}" if moto_id is not None else f"person_{tr_id}"

                if confirmed_no_helmet:
                    now = time.time()
                    last_sent = self.reported_violations.get(entity_key, 0)
                    # Mỗi phương tiện / người tối đa 1 biên bản vi phạm trong 30 giây
                    if (now - last_sent) > 30.0:
                        self.reported_violations[entity_key] = now
                        target_label = f"Xe máy #{moto_id}" if moto_id is not None else f"Người #{tr_id}"
                        print(f"🚨 [PHÁT HIỆN VI PHẠM] {target_label} KHÔNG ĐỘI MŨ BẢO HIỂM! (Độ tin cậy: {int(h_conf*100)}%)")

                        # Tạo ảnh bằng chứng sạch gửi Backend
                        evidence = clean_frame.copy()
                        if box is not None:
                            bx1, by1, bx2, by2 = map(int, box)
                            cv2.rectangle(evidence, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
                            cv2.putText(evidence, f"KHONG DOI MU {int(h_conf*100)}%", (bx1, max(20, by1 - 6)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                        send_violation_to_backend(evidence, "NO_HELMET", "MOTORCYCLE", h_conf)
                # TUYỆT ĐỐI KHÔNG CÓ NHÁNH ELSE XÓA KEY (Tránh spam lặp lại khi xe chở 2 người 1 có 1 không mũ)
            except Exception as e:
                print(f"[ViT Worker Error] {e}")
            finally:
                if tr_id in self.processing_tracks:
                    self.processing_tracks.remove(tr_id)
                self.queue.task_done()

def find_riders(tracked_objects, is_standalone=False):
    """
    Xác định người đang điều khiển / ngồi trên xe máy (Riders):
    - is_standalone=True: Cho phép test cá nhân tại nhà không cần xe máy (webcam hoặc ảnh chụp).
    - Video giao thông: Chỉ kiểm tra person có bounding box chồng lấn lên motorcycle.
    Trả về dict: {person_tr_id: moto_tr_id}
    """
    persons = [o for o in tracked_objects if o["class_name"] == "person"]
    motos = [o for o in tracked_objects if o["class_name"] == "motorcycle"]

    if is_standalone:
        return {p["tracker_id"]: None for p in persons}

    if len(motos) == 0:
        return {} # Trong video giao thông nếu không có xe máy nào thì không bắt người đi bộ

    riders = {}
    for p in persons:
        px1, py1, px2, py2 = p["box"]
        p_area = max(1.0, (px2 - px1) * (py2 - py1))
        pcx = (px1 + px2) / 2.0

        best_moto_id = None
        max_overlap = 0.0

        for m in motos:
            mx1, my1, mx2, my2 = m["box"]
            ix = max(0.0, min(px2, mx2) - max(px1, mx1))
            iy = max(0.0, min(py2, my2) - max(py1, my1))
            inter_area = ix * iy

            overlap_ratio = inter_area / p_area
            # Điều kiện:
            # 1. Chồng lấn diện tích >= 20%
            # 2. Tâm ngang của người phải nằm TRONG chiều ngang xe máy (loại bỏ người đứng cạnh xe)
            # 3. Đỉnh đầu người phải ở nửa trên xe
            if overlap_ratio > 0.20 and (mx1 <= pcx <= mx2) and py1 < (my1 + (my2 - my1) * 0.6):
                if overlap_ratio > max_overlap:
                    max_overlap = overlap_ratio
                    best_moto_id = m["tracker_id"]

        if best_moto_id is not None:
            riders[p["tracker_id"]] = best_moto_id

    return riders

def main():
    global latest_jpeg
    print("=" * 65)
    print("🚦 HỆ THỐNG GIÁM SÁT GIAO THÔNG AI (PBL4 - NHÓM 3) 🚦")
    print("=" * 65)

    # Khởi chạy Flask Server cung cấp luồng Video trực tiếp (Port 5000) cho Web App
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    print("🌐 [LIVE STREAM] Server phát luồng Web mở tại: http://localhost:5000/video_feed")
    print("📡 [LIVE STATUS] API kiểm tra camera tại: http://localhost:5000/status")

    # 1. Khởi tạo Mô hình Nhận diện YOLO11 (Real-time 30 FPS)
    from detectors.yolo_detector import YoloDetector
    yolo_model = getattr(config, "YOLO_MODEL_NAME", "yolo11n.pt")
    print(f"🚀 [MÔ HÌNH NHẬN DIỆN] YOLO11 ({yolo_model}) - 30 FPS thời gian thực")
    detector = YoloDetector(model_name=yolo_model)
    mode_label = f"YOLO11 ({yolo_model})"

    # 2. Khởi tạo ByteTrack và ViT Worker
    tracker = ByteTrackerManager()
    helmet_clf = HelmetClassifier()
    vit_worker = AsyncViTWorker(helmet_clf)

    # 3. Khởi chạy luồng ngầm lắng nghe đèn MQTT
    mqtt_client = start_light_listener()

    dataset_video = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset", "traffic2.mp4"))
    default_source = dataset_video if os.path.exists(dataset_video) else "0"

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=default_source, help="Video path or webcam index")
    parser.add_argument("--no-gui", action="store_true", help="Chạy chế độ nền không hiện cửa sổ OpenCV")
    parser.add_argument("--standalone", action="store_true", help="Chế độ test mũ bảo hiểm cá nhân (không yêu cầu xe máy)")
    args, _ = parser.parse_known_args()

    source = int(args.source) if args.source.isdigit() else args.source

    # KIỂM TRA NẾU NGUỒN VÀO LÀ FILE ẢNH TĨNH (.jpg, .png, .jpeg...)
    is_image = isinstance(source, str) and os.path.isfile(source) and source.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))
    if is_image:
        print(f"📸 [CHẾ ĐỘ TEST ẢNH TĨNH] Đang phân tích file ảnh: '{source}'...")
        raw_img = cv2.imread(source)
        if raw_img is None:
            print("❌ Không thể đọc file ảnh (file hỏng hoặc sai định dạng).")
            return

        frame = raw_img.copy()
        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        clean_frame = frame.copy()

        h, w = frame.shape[:2]
        stream_metrics["width"] = w
        stream_metrics["height"] = h

        detections = detector.detect(frame)
        found_targets = 0

        for idx, obj in enumerate(detections):
            x1, y1, x2, y2 = map(int, obj["box"])
            cls_name = obj["class_name"]

            if cls_name == "person":
                found_targets += 1
                # Cắt chuẩn xác vùng đầu từ clean_frame (trung tâm 55% chiều ngang, 28% chiều cao đỉnh đầu)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]

                is_no_helmet, conf = helmet_clf.predict_head(head_crop)

                if is_no_helmet:
                    box_color = (0, 0, 255) # Đỏ
                    label = f"[KO MU] {int(conf * 100)}%"
                    text_color = (255, 255, 255)
                    print(f"🚨 Người #{found_targets}: KHÔNG ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")
                    send_violation_to_backend(frame, "NO_HELMET", "MOTORCYCLE", conf)

                    # Chỉ vẽ viền đỏ nổi bật cho người KHÔNG ĐỘI MŨ
                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                    font_scale = 0.5
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
                    badge_y = max(th + 6, y1)
                    cv2.rectangle(frame, (x1, badge_y - th - 4), (x1 + tw + 6, badge_y + 2), box_color, -1)
                    cv2.putText(frame, label, (x1 + 3, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
                else:
                    # Người CÓ ĐỘI MŨ: Tuyệt đối không vẽ gì lên ảnh để giữ màn hình sạch sẽ, không rối mắt
                    print(f"✅ Người #{found_targets}: CÓ ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")

        # Nếu là ảnh chụp cận cảnh đầu (YOLO không nhận diện được toàn thân)
        if found_targets == 0:
            is_no_helmet, conf = helmet_clf.predict_head(frame)
            if is_no_helmet:
                box_color = (0, 0, 255)
                label = f"[KO MU] {int(conf * 100)}%"
                text_color = (255, 255, 255)
                print(f"🚨 KẾT QUẢ CẬN CẢNH: KHÔNG ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")
                send_violation_to_backend(frame, "NO_HELMET", "MOTORCYCLE", conf)

                cv2.rectangle(frame, (10, 10), (w - 10, h - 10), box_color, 3)
                font_scale = 0.7
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
                cv2.rectangle(frame, (10, 10 + th + 10), (10 + tw + 10, 10), box_color, -1)
                cv2.putText(frame, label, (15, 10 + th + 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
            else:
                print(f"✅ KẾT QUẢ CẬN CẢNH: CÓ ĐỘI MŨ (Độ tin cậy: {int(conf * 100)}%)")

        ret_enc, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_enc:
            with frame_lock:
                latest_jpeg = buffer.tobytes()

        if not args.no_gui:
            cv2.imshow("PBL4 - Traffic Monitor AI (YOLO11n + ViT Helmet)", frame)
            print("\n🖥️ Đang hiện cửa sổ kết quả (Bấm phím bất kỳ trên cửa sổ ảnh để thoát)...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        vit_worker.running = False
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
            except Exception:
                pass
        return

    cap = cv2.VideoCapture(source)

    prev_positions = {}      # Lưu tọa độ mép trước (front Y): {tracker_id: front_y}
    track_class_history = {} # Lưu lịch sử nhãn để ổn định lớp: {tracker_id: [classes]}

    fps_count = 0
    start_time = time.time()
    fps_display = 0

    print("\n💡 HƯỚNG DẪN ĐIỀU KHIỂN:")
    print("   + Bấm phím 'r': Bật cưỡng bức Đèn ĐỎ (test phạt vượt đèn đỏ)")
    print("   + Bấm phím 'y': Bật cưỡng bức Đèn VÀNG (giảm tốc/chuẩn bị dừng)")
    print("   + Bấm phím 'g': Bật lại Đèn XANH (lưu thông bình thường)")
    print("   + Bấm phím 'q': Thoát chương trình\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            if isinstance(source, str) and os.path.exists(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                tracker = ByteTrackerManager()
                prev_positions.clear()
                track_class_history.clear()
                vs.reset_tracking_state()
                continue
            print("Đã hết video hoặc không thể đọc camera.")
            break

        # Tự động co tỷ lệ video độ phân giải cao về vừa vặn màn hình laptop (chiều cao 720px)
        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        # Lưu bản copy sạch (không bị vẽ chữ/vạch đè lên) để làm bằng chứng vi phạm
        clean_frame = frame.copy()

        h, w = frame.shape[:2]
        stream_metrics["width"] = w
        stream_metrics["height"] = h
        stop_line_y = int(h * 0.65) # Vạch dừng nằm ở 65% chiều cao khung hình

        # Nhận diện xe với Detector
        detections = detector.detect(frame)

        # Cập nhật bám đuôi với ByteTrack
        tracked_objects = tracker.update(detections)

        # 1. Vẽ Vạch Dừng - Gọn gàng mảnh 2px, không vẽ khối mờ che mặt đường
        line_color = (0, 0, 255) if vs.current_traffic_light == "RED" else (0, 200, 0)
        cv2.line(frame, (0, stop_line_y), (w, stop_line_y), line_color, 2)
        cv2.putText(frame, "VACH DUNG", (10, stop_line_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, line_color, 1)

        # 2. Xác định người ngồi trên xe máy (Riders)
        is_standalone = args.standalone or isinstance(source, int)
        riders_map = find_riders(tracked_objects, is_standalone=is_standalone)

        active_tr_ids = set()

        # Duyệt qua từng đối tượng đang được theo dõi
        for obj in tracked_objects:
            x1, y1, x2, y2 = map(int, obj["box"])
            tr_id = obj["tracker_id"]
            raw_cls = obj["class_name"]
            conf = obj["score"]
            active_tr_ids.add(tr_id)

            # ỔN ĐỊNH LỚP (Class Stabilization): Tránh hiện tượng nhấp nháy khi YOLO đổi qua lại giữa person và motorcycle
            if tr_id not in track_class_history:
                track_class_history[tr_id] = []
            track_class_history[tr_id].append(raw_cls)
            if len(track_class_history[tr_id]) > 20:
                track_class_history[tr_id].pop(0)

            history = track_class_history[tr_id]
            if "motorcycle" in history:
                cls_name = "motorcycle"
            elif "truck" in history:
                cls_name = "truck"
            elif "bus" in history:
                cls_name = "bus"
            elif "car" in history:
                cls_name = "car"
            else:
                cls_name = max(set(history), key=history.count)

            # Tính tọa độ mép trước (Leading Edge / Front Bumper) của phương tiện
            # Chiều xe đi lên (Y giảm dần như traffic2.mp4): mép trước là y1 (đỉnh trên của box)
            # Chiều xe đi xuống (Y tăng dần): mép trước là y2 (đáy dưới của box)
            is_moving_up = (tr_id in prev_positions and y1 < prev_positions[tr_id]) or (y2 >= stop_line_y)
            curr_front_y = y1 if is_moving_up else y2
            prev_front_y = prev_positions.get(tr_id, curr_front_y)

            # A. KIỂM TRA LỖI VƯỢT ĐÈN ĐỎ & LƯU LƯỢNG XE (bắt ngay lập tức khi đầu xe chạm vạch)
            is_violating_red_light = check_red_light_violation(
                tr_id, prev_front_y, curr_front_y, clean_frame, cls_name, conf, stop_line_y=stop_line_y, box=obj["box"]
            )
            if tr_id in prev_positions:
                check_traffic_flow(
                    tr_id, prev_front_y, curr_front_y, cls_name, stop_line_y=stop_line_y
                )
            prev_positions[tr_id] = curr_front_y

            # B. KIỂM TRA MŨ BẢO HIỂM (Chỉ kiểm tra người điều khiển xe máy)
            if raw_cls == "person" or cls_name == "motorcycle":
                moto_id = riders_map.get(tr_id, tr_id if cls_name == "motorcycle" else None)
                cx = (x1 + x2) // 2
                hw = int((x2 - x1) * 0.55)
                # Cắt từ clean_frame để tránh dính nét vẽ/vạch dừng
                head_crop = clean_frame[max(0, y1):min(h, y1 + int((y2 - y1) * 0.28)), max(0, cx - hw // 2):min(w, cx + hw // 2)]
                
                # Ngưỡng tối thiểu 14px phù hợp với kích thước thực tế của đầu người trong video giao thông
                if head_crop.size > 0 and head_crop.shape[0] >= 14 and head_crop.shape[1] >= 14:
                    vit_worker.submit(tr_id, head_crop, clean_frame, moto_id=moto_id, box=obj["box"])

            is_no_helmet, h_conf, _ = vit_worker.get_status(tr_id)

            # C. VẼ BOUNDING BOX - Ổn định, dày 2px, nhãn có nền màu, tuyệt đối KHÔNG NHẤP NHÁY
            if is_violating_red_light:
                # Vi phạm vượt đèn đỏ: Viền đỏ 2px + nền nhãn đỏ nổi bật
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                label = f"[VUOT DEN] #{tr_id}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                by = max(th + 4, y1)
                cv2.rectangle(frame, (x1, by - th - 4), (x1 + tw + 6, by + 2), (0, 0, 255), -1)
                cv2.putText(frame, label, (x1 + 3, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            elif is_no_helmet:
                # Vi phạm không đội mũ: Viền đỏ 2px + nền nhãn đỏ nổi bật
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                label = f"[KO MU] #{tr_id}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                by = max(th + 4, y1)
                cv2.rectangle(frame, (x1, by - th - 4), (x1 + tw + 6, by + 2), (0, 0, 255), -1)
                cv2.putText(frame, label, (x1 + 3, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            else:
                # Phương tiện bình thường: Giữ viền Cyan-Amber liên tục trên mọi frame (chống biến mất/nhấp nháy)
                box_c = (220, 160, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_c, 2)
                display_label = "rider" if cls_name == "person" else cls_name
                label = f"{display_label} #{tr_id}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
                by = max(th + 4, y1)
                cv2.rectangle(frame, (x1, by - th - 4), (x1 + tw + 4, by + 2), box_c, -1)
                cv2.putText(frame, label, (x1 + 2, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

        # D. DỌN DẸP BỘ NHỚ ĐỊNH KỲ (Tránh rò rỉ RAM)
        if fps_count % 30 == 0:
            vit_worker.cleanup_old_tracks(active_tr_ids)
            stale_keys = [k for k in prev_positions if k not in active_tr_ids]
            if len(stale_keys) > 40:
                for k in stale_keys[:20]:
                    prev_positions.pop(k, None)
                    track_class_history.pop(k, None)

        # Hiển thị FPS và Đèn trên góc trái - Gọn gàng tinh tế
        fps_count += 1
        if time.time() - start_time >= 1.0:
            fps_display = fps_count
            fps_count = 0
            start_time = time.time()
            stream_metrics["fps"] = fps_display

        light_color = (0, 0, 255) if vs.current_traffic_light == "RED" else (0, 200, 0)
        cv2.circle(frame, (16, 20), 7, light_color, -1)
        cv2.circle(frame, (16, 20), 8, (255, 255, 255), 1)
        cv2.putText(frame, f"DEN: {vs.current_traffic_light}  |  FPS: {fps_display}", (32, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Cập nhật buffer phát sóng trực tiếp qua mạng HTTP MJPEG
        ret_enc, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret_enc:
            with frame_lock:
                latest_jpeg = buffer.tobytes()

        # Hiển thị cửa sổ OpenCV (nếu bật GUI)
        if not args.no_gui:
            try:
                cv2.imshow("PBL4 - Traffic Monitor AI (YOLO11n + ViT Helmet)", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    vs.set_manual_light("RED")
                elif key == ord('y'):
                    vs.set_manual_light("YELLOW")
                elif key == ord('g'):
                    vs.set_manual_light("GREEN")
                elif key == ord('a'):
                    vs.reset_to_auto_esp32()
            except Exception:
                time.sleep(0.02)
        else:
            time.sleep(0.025)

    vit_worker.running = False
    cap.release()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    if mqtt_client:
        mqtt_client.loop_stop()

if __name__ == "__main__":
    main()
