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

    # B5: Giới hạn kích thước/thất lượng ảnh bằng chứng trước khi gửi lên Cloudinary + MySQL.
    # Trước đây dùng cv2.imencode mặc định (JPEG quality 95, không resize): ảnh 720p ~500-700KB,
    # base64 phình thêm 33% -> mỗi request ~1MB, dễ timeout (timeout cũ 25s) và tốn dung lượng.
    EVIDENCE_MAX_WIDTH = 1280
    EVIDENCE_JPEG_QUALITY = 85

    def __init__(self, endpoint=None):
        self.violation_endpoint = endpoint or getattr(config, "VIOLATION_ENDPOINT", "http://localhost:8080/api/violations")
        self.flow_endpoint = "http://localhost:8080/api/stats/flow"
        self.camera_id = getattr(config, "CAMERA_ID", 1)

    def set_camera_id(self, camera_id):
        """C4: cập nhật camera đang giám sát để biên bản gắn đúng camera trong DB."""
        self.camera_id = int(camera_id)

    def _async_post_violation(self, payload):
        try:
            res = requests.post(self.violation_endpoint, json=payload, timeout=25)
            if res.status_code in [200, 201]:
                data = res.json()
                # Backend chỉ trả {id, status} nên tránh in "None VNĐ" gây hiểu nhầm
                fine = data.get('fineAmount')
                fine_note = f" | Mức phạt: {fine} VNĐ" if fine is not None else ""
                print(f"✅ [BACKEND] Gửi vi phạm thành công! ID #{data.get('id')}{fine_note}")
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

    def _encode_evidence(self, frame_bgr):
        """B5: Thu nhỏ (nếu cần) + nén JPEG vừa đủ nét để giảm dung lượng ảnh bằng chứng."""
        if frame_bgr is None or frame_bgr.size == 0:
            raise ValueError("Khung hình bằng chứng rỗng")

        h, w = frame_bgr.shape[:2]
        if w > self.EVIDENCE_MAX_WIDTH:
            scale = self.EVIDENCE_MAX_WIDTH / float(w)
            frame_bgr = cv2.resize(
                frame_bgr,
                (self.EVIDENCE_MAX_WIDTH, max(1, int(round(h * scale)))),
                interpolation=cv2.INTER_AREA  # INTER_AREA cho ảnh thu nhỏ: nét hơn, ít răng cưa
            )

        ok, buffer = cv2.imencode(
            '.jpg', frame_bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.EVIDENCE_JPEG_QUALITY]
        )
        if not ok:
            raise RuntimeError("Không nén được ảnh bằng chứng sang JPEG")
        return buffer

    def send_violation(self, frame_bgr, violation_type, vehicle_type, confidence, camera_id=None):
        """
        Mã hóa ảnh BGR sang Base64 và đẩy sang Spring Boot qua luồng ngầm.
        C4: `camera_id` nên được chụp tại thời điểm phát hiện (ViT Worker chạy async —
        nếu người dùng đổi camera trong lúc chờ thì biên bản vẫn gắn đúng camera cũ).
        """
        buffer = self._encode_evidence(frame_bgr)
        b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

        payload = {
            "cameraId": self.camera_id if camera_id is None else int(camera_id),
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
