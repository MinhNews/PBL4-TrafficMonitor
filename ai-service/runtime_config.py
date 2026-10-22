"""
C2: Cấu hình runtime của AI Engine — chỉnh trực tiếp từ trang Settings trên Web.

Trước đây muốn đổi vạch dừng hay chiều xe chạy phải sửa tay `config.py` rồi
tắt/mở lại AI. Module này giữ cấu hình đang chạy trong bộ nhớ, cho phép
`POST /config` (Flask port 5000) cập nhật tức thì và lưu xuống
`runtime_config.json` để lần khởi động sau vẫn giữ nguyên.

Giá trị mặc định luôn lấy từ `config.py` (nguồn chân lý gốc của dự án).
"""

import json
import os
import threading

import config

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_BASE_DIR, "runtime_config.json")

# Khoảng hợp lệ của tỉ lệ vạch dừng: tránh người dùng kéo vạch ra ngoài khung hình
MIN_RATIO = 0.05
MAX_RATIO = 0.95
VALID_DIRECTIONS = ("up", "down")

DEFAULTS = {
    "stopLineRatio": round(float(getattr(config, "STOP_LINE_RATIO", 0.65)), 3),
    "approachDirection": str(getattr(config, "APPROACH_DIRECTION", "up")).strip().lower(),
    # C4: chỉ ảnh hưởng việc VẼ vạch, logic tính vi phạm vẫn dùng stopLineRatio
    "stopLineVisible": bool(getattr(config, "STOP_LINE_VISIBLE", True)),
}

_lock = threading.RLock()
_settings = dict(DEFAULTS)


def _sanitize(payload, base):
    """Kiểm tra và chuẩn hoá dữ liệu gửi lên. Trả (cấu hình mới, danh sách lỗi)."""
    result = dict(base)
    errors = []

    if "stopLineRatio" in payload and payload["stopLineRatio"] is not None:
        try:
            ratio = float(payload["stopLineRatio"])
            if MIN_RATIO <= ratio <= MAX_RATIO:
                result["stopLineRatio"] = round(ratio, 3)
            else:
                errors.append(f"stopLineRatio phải nằm trong khoảng {MIN_RATIO} – {MAX_RATIO}")
        except (TypeError, ValueError):
            errors.append("stopLineRatio phải là số (ví dụ 0.65)")

    if "approachDirection" in payload and payload["approachDirection"] is not None:
        direction = str(payload["approachDirection"]).strip().lower()
        if direction in VALID_DIRECTIONS:
            result["approachDirection"] = direction
        else:
            errors.append("approachDirection chỉ nhận 'up' hoặc 'down'")

    if "stopLineVisible" in payload and payload["stopLineVisible"] is not None:
        visible = payload["stopLineVisible"]
        if isinstance(visible, bool):
            result["stopLineVisible"] = visible
        elif isinstance(visible, (int, float)) and visible in (0, 1):
            result["stopLineVisible"] = bool(visible)
        elif isinstance(visible, str) and visible.strip().lower() in ("true", "false", "1", "0"):
            result["stopLineVisible"] = visible.strip().lower() in ("true", "1")
        else:
            errors.append("stopLineVisible chỉ nhận true/false")

    return result, errors


def _save():
    """Ghi cấu hình ra JSON. Lỗi ghi file không làm hỏng AI (vẫn chạy bằng RAM)."""
    try:
        tmp_path = _PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_settings, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _PATH)
    except OSError as e:
        print(f"⚠️ [RUNTIME CONFIG] Không lưu được {os.path.basename(_PATH)}: {e}")


def load():
    """Nạp cấu hình đã lưu (nếu có) khi AI khởi động."""
    global _settings
    if not os.path.exists(_PATH):
        return get_settings()
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            raise ValueError("nội dung không phải object JSON")
        with _lock:
            # Chỉ nhận các khoá đã biết, giá trị sai sẽ quay về mặc định
            merged, errors = _sanitize(saved, DEFAULTS)
            if errors:
                print(f"⚠️ [RUNTIME CONFIG] Bỏ qua giá trị không hợp lệ: {', '.join(errors)}")
            _settings = merged
        print(f"⚙️ [RUNTIME CONFIG] Đã nạp: vạch dừng {_settings['stopLineRatio']} · chiều {_settings['approachDirection']} · hiển thị vạch: {'có' if _settings['stopLineVisible'] else 'không'}")
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"⚠️ [RUNTIME CONFIG] File cấu hình lỗi ({e}), dùng mặc định từ config.py.")
        _settings = dict(DEFAULTS)
    return get_settings()


def get_settings():
    with _lock:
        return dict(_settings)


def get_defaults():
    return dict(DEFAULTS)


def apply(payload):
    """
    Áp dụng cấu hình mới. Trả (ok, errors, settings).
    Chỉ ghi file khi thực sự có thay đổi hợp lệ.
    """
    with _lock:
        new_settings, errors = _sanitize(payload or {}, _settings)
        if errors:
            return False, errors, dict(_settings)
        if new_settings != _settings:
            _settings.update(new_settings)
            _save()
            print(f"⚙️ [RUNTIME CONFIG] Cập nhật: vạch dừng {_settings['stopLineRatio']} · chiều {_settings['approachDirection']} · hiển thị vạch: {'có' if _settings['stopLineVisible'] else 'không'}")
        return True, [], dict(_settings)


def reset():
    """Trả về mặc định trong config.py (dùng cho nút 'Khôi phục mặc định')."""
    with _lock:
        _settings.update(DEFAULTS)
        _save()
        return dict(_settings)


def stop_line_ratio():
    """Đọc nhanh mỗi frame — không cần lock vì chỉ đọc 1 float bất biến."""
    return _settings["stopLineRatio"]


def approach_direction():
    return _settings["approachDirection"]


def stop_line_visible():
    """C4: chỉ quyết định có vẽ vạch lên video hay không."""
    return _settings["stopLineVisible"]
