# ===== BACKEND =====
BACKEND_URL = "http://localhost:8080"
VIOLATION_ENDPOINT = f"{BACKEND_URL}/api/violations"
# Khoá chia sẻ để AI Service gọi API ghi dữ liệu khi Backend đã bật Spring Security
# (phải trùng app.ai.api-key trong backend/src/main/resources/application.properties)
AI_API_KEY = "pbl4-nhom3-ai-service-2026"

# ===== DANH SÁCH CAMERA (C4) =====
# AI chỉ chạy MỘT camera tại một thời điểm; Web đổi camera không cần restart.
# Thêm/bớt camera là việc triển khai (hiếm) -> sửa danh sách này rồi khởi động lại AI.
#   - "source": đường dẫn file video (tương đối từ ai-service/), "0" = webcam, hoặc "rtsp://..."
#   - Vạch dừng & chiều xe dùng CHUNG cho mọi camera, chỉnh live trên Web (runtime_config.json)
CAMERAS = [
    {
        "id": 1,
        "name": "Camera 01 - Hòa Khánh",
        "source": "dataset/traffic2.mp4",
    },
    {
        "id": 2,
        "name": "Camera 02 - Hướng Đông",
        "source": "dataset/videokodoimu.mp4",
    },
]

DEFAULT_CAMERA_ID = 1          # Camera bật lên đầu tiên khi khởi động AI
CAMERA_ID = DEFAULT_CAMERA_ID  # Giữ tên cũ để tương thích với BackendService

# ===== MQTT (D2: Cần đồng bộ chính xác với firmware ESP32) =====
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_LIGHT = "pbl4/nhom3/traffic/light"

# ===== CAMERA GEOMETRY (D1) =====
APPROACH_DIRECTION = "up"  # "up" (xe đi lên, Y giảm dần) hoặc "down" (xe đi xuống, Y tăng dần)
STOP_LINE_RATIO = 0.65     # Vị trí vạch dừng ngã tư tính theo tỷ lệ chiều cao khung hình (0.65 = 65%)
STOP_LINE_VISIBLE = True   # Có vẽ vạch dừng lên video hay không (chỉ ảnh hưởng hiển thị, không ảnh hưởng logic)

# ===== AI THRESHOLDS =====
YOLO_CONFIDENCE_THRESHOLD = 0.25
VIT_CONFIDENCE_THRESHOLD = 0.85
NO_HELMET_FRAMES_REQUIRED = 3

# ===== TRACKER / RE-IDENTIFICATION =====
# ByteTrack giữ nguyên buffer 30 frame; lớp stable-ID bên dưới lo các cú mất track dài hơn.
# Ngưỡng match 0.8 = IoU >= 0.2 (0.6 là CHẶT HƠN, dễ đổi ID).
TRACK_LOST_BUFFER = 30          # giữ nguyên mặc định (30 frame)
TRACK_MATCH_THRESHOLD = 0.8     # giữ nguyên mặc định; tăng lên 0.9 làm ByteTrack ghép sai lớp
# Lớp stable-ID: khi ByteTrack cấp ID mới cho xe vừa bị che, thử gán lại ID cũ
# dựa trên class + vị trí dự đoán + thời gian. Tắt bằng TRACK_REID_ENABLED=False.
TRACK_REID_ENABLED = True
TRACK_REID_TTL_FRAMES = 45      # giữ ký ức tối đa 45 frame đã xử lý (~1.5s video 30fps)
TRACK_REID_MIN_SCORE = 0.20     # điểm khớp tối thiểu (0..1); 0.35 quá chặt sau occlusion
TRACK_REID_GATE = 2.0           # bán kính tìm kiếm theo đường chéo box cuối (2.0 = vừa phải)
TRACK_ENTITY_TTL_SEC = 15.0     # giữ entity/state lâu hơn TTL re-ID để không mất lịch sử

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


