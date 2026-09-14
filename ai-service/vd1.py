import sys
import io
import json
import os
from datetime import datetime
import config

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("🚀 Khởi chạy Ví dụ 1 (vd1.py): Ghi thông tin giám sát giao thông vào file vd1.json...")

# 1. Giả lập một dữ liệu sự kiện vi phạm giao thông (Phát hiện từ DETR AI + IoT)
violation_data = {
    "system_info": {
        "camera_id": config.CAMERA_ID,
        "backend_url": config.BACKEND_URL,
        "mqtt_broker": config.MQTT_BROKER,
        "detr_threshold": config.DETR_CONFIDENCE_THRESHOLD,
        "stop_line_y": config.STOP_LINE_Y
    },
    "event_info": {
        "event_id": "EVT_20260914_001",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traffic_light_state": "RED",
        "vehicle_details": {
            "track_id": 1042,
            "class_name": "car",
            "confidence": 0.964,
            "license_plate": "43A-982.11",
            "bbox_coords": [120, 310, 280, 410]  # [xmin, ymin, xmax, ymax]
        },
        "violation_type": "RED_LIGHT_RUNNING",
        "action_taken": "LOGGED_AND_NOTIFIED"
    }
}

# 2. Đường dẫn file đầu ra (vd1.json)
output_filename = "vd1.json"

# 3. Ghi dữ liệu vào file dạng JSON
try:
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(violation_data, f, ensure_ascii=False, indent=4)
    print(f"✅ ĐÃ LƯU THÀNH CÔNG DỮ LIỆU VÀO FILE: {os.path.abspath(output_filename)}")
except Exception as e:
    print(f"❌ Lỗi khi ghi file: {e}")

# 4. Đọc lại file vd1.json để kiểm tra nội dung vừa lưu
print("\n📖 Nội dung tệp vd1.json vừa ghi:")
with open(output_filename, "r", encoding="utf-8") as f:
    print(f.read())
