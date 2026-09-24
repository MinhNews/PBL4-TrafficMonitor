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
PROCESS_EVERY_N_FRAMES = 1  # Chạy AI mỗi 1 frame để tăng FPS

# ===== AI THRESHOLDS =====
# Ngưỡng tin cậy 0.22: Bắt dính liên tục mọi xe máy ở xa (30-40%), triệt tiêu hoàn toàn hiện tượng nhấp nháy
DETR_CONFIDENCE_THRESHOLD = 0.22
VIT_CONFIDENCE_THRESHOLD = 0.85
NO_HELMET_FRAMES_REQUIRED = 5

# ===== DUAL-MODE DETECTOR (Chuyển đổi linh hoạt giữa YOLO và Deformable DETR) =====
# "yolo"           : Chạy YOLO11 siêu mượt 30 FPS thời gian thực cho demo thực chiến
# "deformable_detr": Chạy SenseTime/deformable-detr cho báo cáo lý thuyết đồ án
DETECTOR_BACKEND = "yolo"

# Phiên bản YOLO sử dụng (tự động tải về):
# "yolo11n.pt" : Bản Nano (2.6M params) - 30 FPS mượt nhất, siêu nhẹ
# "yolo11s.pt" : Bản Small (9.4M params)
# "yolo11m.pt" : Bản Medium (20M params) - Độ chính xác cao
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

