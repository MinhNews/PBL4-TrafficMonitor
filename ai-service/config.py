# ===== BACKEND =====
BACKEND_URL = "http://localhost:8080"
VIOLATION_ENDPOINT = f"{BACKEND_URL}/api/violations"
CAMERA_ID = 1

# ===== MQTT =====
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_LIGHT = "traffic/light"

# ===== CAMERA =====
WEBCAM_INDEX = 0  # 0=webcam mặc định
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
PROCESS_EVERY_N_FRAMES = 3  # Chạy AI mỗi 3 frame để tăng FPS

# ===== AI THRESHOLDS =====
DETR_CONFIDENCE_THRESHOLD = 0.7
VIT_CONFIDENCE_THRESHOLD = 0.85
NO_HELMET_FRAMES_REQUIRED = 5

# ===== CAMERA GEOMETRY =====
STOP_LINE_Y = 320  # Điều chỉnh sau khi đặt camera thật

# ===== FLASK STREAM =====
FLASK_PORT = 5000
MJPEG_FPS = 15

# DETR COCO class IDs cần theo dõi
COCO_CLASSES_OF_INTEREST = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}
