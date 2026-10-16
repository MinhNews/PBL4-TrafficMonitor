import sys, os, base64, requests, threading, cv2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

class BackendService:
    """
    Dịch vụ giao tiếp mạng với Backend Spring Boot (localhost:8080).
    - Đẩy biên bản vi phạm kèm ảnh Base64
    - Đẩy số liệu lưu lượng phương tiện
    - Hoạt động 100% bất đồng bộ (Asynchronous Threading) để giữ FPS video ổn định 30 FPS
    """
    def __init__(self, endpoint=None):
        self.violation_endpoint = endpoint or getattr(config, "VIOLATION_ENDPOINT", "http://localhost:8080/api/violations")
        self.flow_endpoint = "http://localhost:8080/api/stats/flow"
        self.camera_id = getattr(config, "CAMERA_ID", 1)

    def _async_post_violation(self, payload):
        try:
            res = requests.post(self.violation_endpoint, json=payload, timeout=25)
            if res.status_code in [200, 201]:
                data = res.json()
                print(f"✅ [BACKEND] Gửi vi phạm thành công! ID #{data.get('id')} | Mức phạt: {data.get('fineAmount')} VNĐ")
            else:
                print(f"⚠️ [BACKEND] Phản hồi HTTP {res.status_code}: {res.text}")
        except requests.exceptions.ConnectionError:
            print(f"ℹ️ [BACKEND] Backend chưa bật (localhost:8080). Đã ghi nhận vi phạm trên hệ thống AI!")
        except Exception as e:
            print(f"⚠️ [BACKEND] Lỗi gửi API vi phạm: {e}")

    def _async_post_flow(self, payload):
        try:
            requests.post(self.flow_endpoint, json=payload, timeout=3)
        except Exception:
            pass

    def send_violation(self, frame_bgr, violation_type, vehicle_type, confidence):
        """Mã hóa ảnh BGR sang Base64 và đẩy sang Spring Boot qua luồng ngầm"""
        _, buffer = cv2.imencode('.jpg', frame_bgr)
        b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        payload = {
            "cameraId": self.camera_id,
            "violationType": str(violation_type),
            "vehicleType": str(vehicle_type).upper(),
            "confidence": round(float(confidence), 2),
            "imageBase64": b64_str
        }
        threading.Thread(target=self._async_post_violation, args=(payload,), daemon=True).start()

    def send_traffic_flow(self, count=1, vehicle_type="car"):
        """Gửi số lượt phương tiện qua ngã tư qua luồng ngầm"""
        payload = {
            "cameraId": self.camera_id,
            "count": int(count),
            "vehicleType": str(vehicle_type).lower()
        }
        threading.Thread(target=self._async_post_flow, args=(payload,), daemon=True).start()
