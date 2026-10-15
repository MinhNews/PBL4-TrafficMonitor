# ===== BACKEND =====
BACKEND_URL = "http://localhost:8080"
VIOLATION_ENDPOINT = f"{BACKEND_URL}/api/violations"
CAMERA_ID = 1

# ===== MQTT =====
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_LIGHT = "pbl4/nhom3/traffic/light"

# ===== CAMERA =====
WEBCAM_INDEX = 0  # 0=webcam mặc định
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
PROCESS_EVERY_N_FRAMES = 1  # Chạy AI mỗi 1 frame để tăng FPS

# ===== AI THRESHOLDS =====
YOLO_CONFIDENCE_THRESHOLD = 0.25
VIT_CONFIDENCE_THRESHOLD = 0.85
NO_HELMET_FRAMES_REQUIRED = 3

# ===== OBJECT DETECTOR =====
# Phiên bản YOLO sử dụng: "yolo11n.pt" (Bản Nano 2.6M params - 30 FPS thời gian thực)
YOLO_MODEL_NAME = "yolo11n.pt"


# ===== CAMERA GEOMETRY =====
STOP_LINE_Y = 320  # Điều chỉnh sau khi đặt camera thật

# ===== FLASK STREAM =====
FLASK_PORT = 5000
MJPEG_FPS = 15

# ===== TARGET CLASSES (Task 2.1: Tránh lỗi lệch nhãn ID giữa các model) =====
# Dùng tên lớp chuẩn tiếng Anh, không phụ thuộc cứng vào số ID:
TARGET_CLASSES = {
    "car",          # Ô tô con
    "motorcycle",   # Xe máy
    "bus",          # Xe buýt
    "truck",        # Xe tải
    "bicycle",      # Xe đạp
    "person"        # Người đi bộ / người điều khiển xe
}

# Ánh xạ ID COCO dự phòng (Fallback):
COCO_CLASSES_OF_INTEREST = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

