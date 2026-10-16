# ===== BACKEND =====
BACKEND_URL = "http://localhost:8080"
VIOLATION_ENDPOINT = f"{BACKEND_URL}/api/violations"
CAMERA_ID = 1

# ===== MQTT (D2: Cần đồng bộ chính xác với firmware ESP32) =====
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_LIGHT = "pbl4/nhom3/traffic/light"

# ===== CAMERA GEOMETRY (D1) =====
APPROACH_DIRECTION = "up"  # "up" (xe đi lên, Y giảm dần) hoặc "down" (xe đi xuống, Y tăng dần)
STOP_LINE_RATIO = 0.65     # Vị trí vạch dừng ngã tư tính theo tỷ lệ chiều cao khung hình (0.65 = 65%)

# ===== AI THRESHOLDS =====
YOLO_CONFIDENCE_THRESHOLD = 0.25
VIT_CONFIDENCE_THRESHOLD = 0.85
NO_HELMET_FRAMES_REQUIRED = 3

# ===== OBJECT DETECTOR =====
YOLO_MODEL_NAME = "yolo11s.pt"  # Bản Small 9.4M params (bắt trọn xe máy và người lái, không bị nhận nhầm thành person)

# ===== WEB STREAM & API =====
FLASK_PORT = 5000

# ===== TARGET CLASSES =====
TARGET_CLASSES = {
    "car",          # Ô tô con
    "motorcycle",   # Xe máy
    "bus",          # Xe buýt
    "truck",        # Xe tải
    "bicycle",      # Xe đạp
    "person"        # Người đi bộ / người điều khiển xe
}

# ===== CÁC THAM SỐ DỰ PHÒNG CHƯA SỬ DỤNG TRỰC TIẾP (D3) =====
# (Được giữ lại để tham chiếu cấu hình phần cứng khi triển khai thực địa)
# WEBCAM_INDEX = 0          # Chỉ số webcam mặc định khi không dùng file video
# FRAME_WIDTH = 640         # Kích thước resize camera mặc định
# FRAME_HEIGHT = 480        # Kích thước resize camera mặc định
# PROCESS_EVERY_N_FRAMES = 1 # Nhảy cóc frame (hiện đang xử lý liên tục từng frame)
# MJPEG_FPS = 15            # Tần số phát luồng video web
# STOP_LINE_Y = 468         # Đã thay thế bằng STOP_LINE_RATIO
# COCO_CLASSES_OF_INTEREST = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}


