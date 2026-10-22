"""
C4: Quản lý nhiều camera nhưng chỉ chạy MỘT camera tại một thời điểm (switch).

Vì sao không chạy song song: trên CPU 6 core, YOLO11s@640 tốn ~133 ms/frame và
ViT phân loại mũ bảo hiểm tốn ~289 ms/lần => chạy 2-3 camera song song chỉ chia
nhỏ tổng FPS (đo thực tế: 1 camera ~4 FPS, 2 camera ~2 FPS mỗi luồng). Switch
giữ nguyên chất lượng của một luồng và đổi nguồn video trong khoảng 1 giây.

Điểm quan trọng: `VideoCapture` của từng camera được giữ lại trong bộ nhớ, nên
khi quay lại camera cũ thì video **phát tiếp đúng vị trí đã dừng** (không tua
lại từ đầu). Camera không phải file cục bộ (webcam/RTSP) được giải phóng khi
rời đi để không giữ thiết bị/kết nối mạng.
"""

import os
import threading
import cv2

# Thư mục ai-service/ (file này nằm trong ai-service/core/)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _normalize_source(raw):
    """Chuẩn hoá nguồn video: webcam index -> int, file tương đối -> đường dẫn tuyệt đối."""
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    if "://" in text:  # rtsp://, http://, ...
        return text
    if os.path.isabs(text):
        return text
    return os.path.normpath(os.path.join(_BASE_DIR, text))


class CameraManager:
    """Giữ danh sách camera, camera đang hoạt động và các VideoCapture đã mở."""

    def __init__(self, cameras=None, initial_id=None):
        cameras = cameras or []
        self._cameras = {}
        for item in cameras:
            try:
                cam_id = int(item["id"])
            except (KeyError, TypeError, ValueError):
                print(f"⚠️ [CAMERA] Bỏ qua cấu hình camera không hợp lệ: {item}")
                continue
            self._cameras[cam_id] = {
                "id": cam_id,
                "name": str(item.get("name") or f"Camera {cam_id}"),
                "source": _normalize_source(item.get("source")),
            }

        if not self._cameras:
            raise ValueError("Không có camera nào trong config.CAMERAS")

        wanted = int(initial_id) if initial_id is not None else next(iter(self._cameras))
        self._active_id = wanted if wanted in self._cameras else next(iter(self._cameras))

        self._pending_id = None
        self._caps = {}
        self._lock = threading.Lock()

        # Cảnh báo sớm nếu file nguồn không tồn tại (không chặn khởi động: có thể là webcam/RTSP sau này)
        for cam in self._cameras.values():
            src = cam["source"]
            if isinstance(src, str) and "://" not in src and not os.path.exists(src):
                print(f"⚠️ [CAMERA] Không tìm thấy nguồn của {cam['name']}: {src}")

    # ------------------------------------------------------------------ thông tin
    def list_cameras(self):
        return [
            {"id": c["id"], "name": c["name"], "active": c["id"] == self._active_id}
            for c in self._cameras.values()
        ]

    def active_camera(self):
        return dict(self._cameras[self._active_id])

    def active_id(self):
        return self._active_id

    def active_name(self):
        return self._cameras[self._active_id]["name"]

    def active_source(self):
        return self._cameras[self._active_id]["source"]

    def describe(self):
        """Thông tin gọn để trả về Web (không lộ đường dẫn file máy chủ)."""
        cam = self._cameras[self._active_id]
        return {"id": cam["id"], "name": cam["name"]}

    # ------------------------------------------------------------------ switch
    def request_switch(self, camera_id):
        """
        Đặt yêu cầu đổi camera. Chỉ ghi cờ, KHÔNG đổi ngay — vòng lặp chính sẽ
        áp dụng giữa hai frame để không tranh chấp với YOLO/ByteTrack.
        Trả (ok, message).
        """
        try:
            cam_id = int(camera_id)
        except (TypeError, ValueError):
            return False, "cameraId phải là số nguyên"

        if cam_id not in self._cameras:
            return False, f"Không có camera id={cam_id}"
        if cam_id == self._active_id:
            return True, "Camera này đang được giám sát"

        with self._lock:
            self._pending_id = cam_id
        return True, "Đang chuyển camera"

    def take_pending(self):
        """Lấy yêu cầu đổi camera đang chờ (nếu có) và xoá cờ."""
        with self._lock:
            pending = self._pending_id
            self._pending_id = None
        return pending

    def pending_id(self):
        with self._lock:
            return self._pending_id

    def set_active(self, camera_id):
        """Áp dụng camera mới. Giải phóng camera cũ nếu nó không phải file cục bộ."""
        old = self._cameras[self._active_id]
        self._active_id = int(camera_id)
        if not self._is_local_file(old):
            self._release_capture(old["id"])

    # ------------------------------------------------------------------ capture
    def open_capture(self, camera_id=None):
        """
        Mở (hoặc lấy lại) VideoCapture của camera. Giữ instance trong bộ nhớ để
        lần quay lại sau phát tiếp đúng khung hình đang dừng.
        Trả None nếu không mở được.
        """
        cam_id = self._active_id if camera_id is None else int(camera_id)
        cam = self._cameras.get(cam_id)
        if cam is None:
            return None

        with self._lock:
            cap = self._caps.get(cam_id)
            if cap is not None and cap.isOpened():
                return cap

            cap = cv2.VideoCapture(cam["source"])
            if not cap.isOpened():
                cap.release()
                return None
            self._caps[cam_id] = cap
            return cap

    def open_active_capture(self):
        return self.open_capture(self._active_id)

    def release_all(self):
        with self._lock:
            for cap in self._caps.values():
                try:
                    cap.release()
                except Exception:
                    pass
            self._caps.clear()

    def _release_capture(self, camera_id):
        with self._lock:
            cap = self._caps.pop(int(camera_id), None)
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    # ------------------------------------------------------------------ tiện ích
    @staticmethod
    def _is_local_file(cam):
        src = cam["source"]
        return isinstance(src, str) and "://" not in src and os.path.isfile(src)

    def active_is_looping(self):
        """Video file cục bộ thì tự tua lại khi hết; webcam/RTSP thì không."""
        return self._is_local_file(self._cameras[self._active_id])

    def active_is_image(self):
        src = self._cameras[self._active_id]["source"]
        return isinstance(src, str) and os.path.isfile(src) and src.lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        )
