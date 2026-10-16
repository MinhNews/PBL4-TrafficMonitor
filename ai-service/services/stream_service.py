import time
import threading
import logging
import cv2
from flask import Flask, Response, jsonify, request

class LiveStreamServer:
    """
    Máy chủ phát luồng video trực tiếp HTTP MJPEG (Port 5000) và cung cấp REST API cho Web Frontend.
    - Phát video mượt mà qua endpoint /video_feed
    - Cung cấp trạng thái camera /status
    - Hỗ trợ đổi đèn thủ công qua API /light (có khóa an toàn khi có ESP32 thật)
    """
    def __init__(self, mqtt_service, violation_engine, port=5000):
        self.mqtt_service = mqtt_service
        self.violation_engine = violation_engine
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
                "timestamp": time.time()
            })

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
