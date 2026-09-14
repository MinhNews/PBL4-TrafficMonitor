import sys
import io
import json
import os
import time
import cv2
import numpy as np
from datetime import datetime
import config

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("🚀 Khởi chạy Ví dụ 2 (vd2.py): Xử lý tệp ảnh img2.jpg, phát hiện vi phạm và lưu vào vd2.json & vd2_result.jpg...")

input_image_path = "img2.jpg"
output_json_path = "vd2.json"
output_image_path = "vd2_result.jpg"

# 1. Nếu chưa có tệp ảnh img2.jpg, tự động tạo 1 ảnh sa bàn giao thông mẫu 640x480
if not os.path.exists(input_image_path):
    print(f"📷 Không thấy tệp {input_image_path}, đang tạo ảnh giao thông sa bàn mẫu 640x480...")
    img = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    img[:] = (40, 40, 40)  # Mặt đường xám thẫm
    
    # Vẽ làn đường (Vạch đứt màu vàng)
    cv2.line(img, (0, 240), (640, 240), (0, 255, 255), 2, cv2.LINE_AA)
    
    # Vẽ vạch dừng (Stop Line tại Y = 320)
    cv2.line(img, (0, config.STOP_LINE_Y), (640, config.STOP_LINE_Y), (255, 255, 255), 4)
    cv2.putText(img, "STOP LINE", (10, config.STOP_LINE_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Vẽ Xe #1 (Ô tô hợp lệ - chưa tới vạch dừng: Y=180 đến Y=260)
    cv2.rectangle(img, (100, 180), (220, 260), (0, 200, 0), -1)
    cv2.putText(img, "Car #101", (105, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # Vẽ Xe #2 (Ô tô VI PHẠM - đang đè/cắt qua vạch dừng: Y=300 đến Y=370)
    cv2.rectangle(img, (380, 300), (520, 370), (0, 0, 220), -1)
    cv2.putText(img, "Car #102 (Violating)", (385, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imwrite(input_image_path, img)
    print(f"✅ Đã tạo ảnh mẫu: {os.path.abspath(input_image_path)}")

# 2. Đọc tệp ảnh img2.jpg
frame = cv2.imread(input_image_path)
if frame is None:
    print(f"❌ Lỗi: Không thể đọc tệp ảnh {input_image_path}")
    sys.exit(1)

# 3. Giả lập kết quả nhận diện từ mô hình DETR AI
detected_objects = [
    {"track_id": 101, "class_name": "car", "confidence": 0.95, "bbox": [100, 180, 220, 260]},
    {"track_id": 102, "class_name": "car", "confidence": 0.98, "bbox": [380, 300, 520, 370]}
]

traffic_light_state = "RED"  # Trạng thái đèn giao thông nhận từ MQTT
stop_line_y = config.STOP_LINE_Y

violations_list = []
annotated_frame = frame.copy()

# Vẽ vạch dừng giao thông lên ảnh
cv2.line(annotated_frame, (0, stop_line_y), (annotated_frame.shape[1], stop_line_y), (0, 0, 255), 3)
cv2.putText(annotated_frame, f"STOP LINE (LIGHT: {traffic_light_state})", (15, stop_line_y - 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

# 4. Vòng lặp kiểm tra vi phạm cắt vạch khi đèn Đỏ
for obj in detected_objects:
    xmin, ymin, xmax, ymax = obj["bbox"]
    track_id = obj["track_id"]
    class_name = obj["class_name"]
    conf = obj["confidence"]
    
    # Kiểm tra nếu phần đuôi/đầu xe đè qua vạch dừng
    is_violating = (traffic_light_state == "RED") and (ymax >= stop_line_y and ymin <= stop_line_y + 60)
    
    if is_violating:
        # Đánh dấu Bounding Box màu ĐỎ nhấp nháy báo vi phạm
        cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 3)
        label = f"VIOLATION! {class_name} #{track_id} ({conf*100:.0f}%)"
        cv2.putText(annotated_frame, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        violations_list.append({
            "violation_id": f"VIO_{track_id}_{int(time.time())}",
            "track_id": track_id,
            "class_name": class_name,
            "confidence": conf,
            "bbox": [xmin, ymin, xmax, ymax],
            "violation_type": "RED_LIGHT_RUNNING",
            "traffic_light": traffic_light_state,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        # Xe hợp lệ -> Bounding Box màu XANH LỤC
        cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        label = f"LEGAL {class_name} #{track_id} ({conf*100:.0f}%)"
        cv2.putText(annotated_frame, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

# 5. Lưu ảnh đã kết xuất Bounding Box vi phạm ra file vd2_result.jpg
cv2.imwrite(output_image_path, annotated_frame)
print(f"🖼️ Đã kết xuất ảnh đánh dấu vi phạm vào: {os.path.abspath(output_image_path)}")

# 6. Tổng hợp dữ liệu kết quả lưu vào file vd2.json
result_data = {
    "execution_info": {
        "script": "vd2.py",
        "input_image": input_image_path,
        "output_annotated_image": output_image_path,
        "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "traffic_light_status": traffic_light_state,
        "stop_line_y": stop_line_y
    },
    "summary": {
        "total_vehicles_detected": len(detected_objects),
        "total_violations_found": len(violations_list)
    },
    "violations": violations_list
}

# Ghi dữ liệu vào file vd2.json
with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(result_data, f, ensure_ascii=False, indent=4)

print(f"✅ ĐÃ LƯU THÀNH CÔNG DỮ LIỆU BÁO CÁO VI PHẠM VÀO FILE: {os.path.abspath(output_json_path)}")

# 7. In nội dung file vd2.json ra màn hình
print("\n📖 Nội dung tệp vd2.json vừa tạo:")
with open(output_json_path, "r", encoding="utf-8") as f:
    print(f.read())
