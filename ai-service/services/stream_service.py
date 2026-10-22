import time
import threading
import logging
import cv2
from flask import Flask, Response, jsonify, request
import runtime_config

class LiveStreamServer:
    """
    Máy chủ phát luồng video trực tiếp HTTP MJPEG (Port 5000) và cung cấp REST API cho Web Frontend.
    - Phát video mượt mà qua endpoint /video_feed
    - Cung cấp trạng thái camera /status
    - Hỗ trợ đổi đèn thủ công qua API /light (có khóa an toàn khi có ESP32 thật)
    """
    def __init__(self, mqtt_service, violation_engine, port=5000, camera_manager=None):
        self.mqtt_service = mqtt_service
        self.violation_engine = violation_engine
        self.camera_manager = camera_manager
        self.port = port
        self.latest_jpeg = None
        self.frame_lock = threading.Lock()
        self.metrics = {"fps": 0, "width": 640, "height": 480}

        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.after_request
        def add_cors(res):
            res.headers['Access-Control-Allow-Origin'] = '*'
            res.headers['Access-Control-Allow-Headers'] = '*'
            res.headers['Access-Control-Allow-Methods'] = '*'
            return res

        def _active_camera_payload():
            """C4: camera đang giám sát + cờ đang chuyển (để Web hiện overlay)."""
            if self.camera_manager is None:
                return None
            payload = self.camera_manager.describe()
            pending = self.camera_manager.pending_id()
            payload["switching"] = pending is not None
            payload["pendingId"] = pending
            return payload

        @self.app.route('/health')
        @self.app.route('/status')
        def status():
            esp32_online = self.mqtt_service.is_esp32_online()
            return jsonify({
                "status": "ONLINE",
                "fps": self.metrics.get("fps", 0),
                "light": self.mqtt_service.current_light,
                "esp32Online": esp32_online,
                "remainingSeconds": self.mqtt_service.remaining_seconds if esp32_online else None,
                "mode": "ESP32_HARDWARE" if esp32_online else "TEST_STANDALONE",
                "vehiclesPassed": len(self.violation_engine.passed_vehicles),
                "violations": self.violation_engine.violation_count,
                "width": self.metrics.get("width", 0),
                "height": self.metrics.get("height", 0),
                "orientation": "PORTRAIT" if self.metrics.get("height", 0) > self.metrics.get("width", 0) else "LANDSCAPE",
                # C2: cấu hình đang chạy thật (để trang Settings hiển thị đồng bộ)
                "stopLineRatio": runtime_config.stop_line_ratio(),
                "approachDirection": runtime_config.approach_direction(),
                # C4: bật/tắt vạch dừng + camera đang giám sát
                "stopLineVisible": runtime_config.stop_line_visible(),
                "activeCamera": _active_camera_payload(),
                "timestamp": time.time()
            })

        @self.app.route('/cameras')
        def cameras():
            """C4: danh sách camera cấu hình trong config.py + camera đang chạy."""
            if self.camera_manager is None:
                return jsonify({"cameras": [], "activeCamera": None})
            return jsonify({
                "cameras": self.camera_manager.list_cameras(),
                "activeCamera": _active_camera_payload(),
            })

        @self.app.route('/camera/switch', methods=['POST'])
        def camera_switch():
            """
            C4: yêu cầu đổi camera. AI áp dụng giữa hai frame (không restart),
            giữ nguyên vị trí phát của camera cũ để quay lại thì phát tiếp.
            """
            if self.camera_manager is None:
                return jsonify({"error": "CAMERA_MANAGER_UNAVAILABLE", "message": "AI chưa cấu hình camera"}), 503

            data = request.get_json(silent=True) or {}
            if "cameraId" not in data:
                return jsonify({"error": "INVALID_CAMERA", "message": "Thiếu cameraId"}), 400

            ok, message = self.camera_manager.request_switch(data.get("cameraId"))
            if not ok:
                return jsonify({"error": "INVALID_CAMERA", "message": message}), 404

            return jsonify({
                "status": "SWITCHING",
                "message": message,
                "activeCamera": _active_camera_payload(),
            }), 202

        @self.app.route('/config', methods=['GET', 'POST'])
        def ai_config():
            """
            C2: Đọc / chỉnh cấu hình vạch dừng ngay khi AI đang chạy.
            GET  -> trả cấu hình hiện tại + giá trị mặc định trong config.py
            POST -> {"stopLineRatio": 0.65, "approachDirection": "up"}
            """
            if request.method == 'GET':
                settings = runtime_config.get_settings()
                defaults = runtime_config.get_defaults()
                return jsonify({
                    "stopLineRatio": settings["stopLineRatio"],
                    "approachDirection": settings["approachDirection"],
                    "stopLineVisible": settings["stopLineVisible"],
                    "defaults": defaults,
                    "isDefault": settings == defaults,
                })

            data = request.get_json(silent=True) or {}
            before = runtime_config.get_settings()
            ok, errors, settings = runtime_config.apply(data)
            if not ok:
                return jsonify({
                    "error": "INVALID_CONFIG",
                    "message": "; ".join(errors),
                    "settings": settings,
                }), 400

            # Áp dụng tức thì cho engine đang chạy, không cần restart
            self.violation_engine.approach_direction = settings["approachDirection"]
            # Chỉ khi vạch/chiều xe đổi thật thì trạng thái "đã qua vạch" của phiên cũ mới sai.
            # C4: bật/tắt hiển thị vạch KHÔNG được làm mất bộ đếm của phiên.
            geometry_changed = (
                settings["stopLineRatio"] != before["stopLineRatio"]
                or settings["approachDirection"] != before["approachDirection"]
            )
            if geometry_changed:
                self.violation_engine.reset()

            return jsonify({
                "status": "APPLIED",
                "message": (
                    "Đã áp dụng cấu hình cho AI đang chạy (bộ đếm phiên AI được làm mới)."
                    if geometry_changed
                    else "Đã áp dụng cấu hình cho AI đang chạy."
                ),
                "settings": settings,
            })

        @self.app.route('/config/reset', methods=['POST'])
        def ai_config_reset():
            """C2: Khôi phục mặc định lấy từ config.py."""
            settings = runtime_config.reset()
            self.violation_engine.approach_direction = settings["approachDirection"]
            self.violation_engine.reset()
            return jsonify({"status": "RESET", "settings": settings})

        @self.app.route('/light', methods=['POST'])
        def set_light():
            if self.mqtt_service.is_esp32_online():
                return jsonify({
                    "error": "ESP32_LOCKED",
                    "message": "Hệ thống khóa can thiệp thủ công để đảm bảo tính xác thực.",
                    "light": self.mqtt_service.current_light,
                    "esp32Online": True
                }), 403

            data = request.get_json(silent=True) or {}
            new_light = data.get("light", "").upper()
            if new_light in ["RED", "GREEN", "YELLOW"]:
                self.mqtt_service.set_manual_light(new_light)
            return jsonify({
                "light": self.mqtt_service.current_light,
                "esp32Online": False,
                "mode": "TEST_STANDALONE"
            })

        @self.app.route('/video_feed')
        def video_feed():
            def generate():
                while True:
                    with self.frame_lock:
                        frame_bytes = self.latest_jpeg
                    if frame_bytes is None:
                        time.sleep(0.04)
                        continue
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    time.sleep(0.033)
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def update_frame(self, frame_bgr, fps=0):
        """Mã hóa frame và cập nhật bộ đệm phát sóng"""
        h, w = frame_bgr.shape[:2]
        self.metrics["width"] = w
        self.metrics["height"] = h
        self.metrics["fps"] = fps

        ret, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            with self.frame_lock:
                self.latest_jpeg = buffer.tobytes()

    def start(self):
        """Khởi chạy máy chủ Flask trên luồng riêng"""
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        t = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, threaded=True, debug=False, use_reloader=False),
            daemon=True
        )
        t.start()
        print(f"🌐 [LIVE STREAM] Server phát luồng Web sẵn sàng tại: http://localhost:{self.port}/video_feed")
        print(f"📡 [LIVE STATUS] API kiểm tra camera sẵn sàng tại: http://localhost:{self.port}/status")
        return self
