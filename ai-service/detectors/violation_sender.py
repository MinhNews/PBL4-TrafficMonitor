import os, sys, cv2, json, base64, requests, time
import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

# Trạng thái đèn tín hiệu hiện tại (mặc định là GREEN)
current_traffic_light = "GREEN"

# Lưu lịch sử vi phạm để không gửi trùng lặp nhiều lần cho cùng 1 xe: {tracker_id: timestamp_violation}
reported_violations = {}

def on_mqtt_message(client, userdata, msg):
    """Lắng nghe trạng thái đèn tín hiệu thời gian thực từ ESP32 / Wokwi qua MQTT"""
    global current_traffic_light
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        if isinstance(data, dict):
            current_traffic_light = data.get("status") or data.get("light") or "GREEN"
        else:
            current_traffic_light = str(data).upper()
    except Exception:
        text = msg.payload.decode('utf-8').strip().strip('"').upper()
        if text in ["RED", "YELLOW", "GREEN"]:
            current_traffic_light = text

def start_light_listener():
    """Khởi chạy luồng ngầm lắng nghe trạng thái đèn giao thông"""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None, client_id="AI_TrafficLight_Listener")
    client.on_message = on_mqtt_message

    broker = getattr(config, "MQTT_BROKER", "test.mosquitto.org")
    port = getattr(config, "MQTT_PORT", 1883)
    topic = getattr(config, "MQTT_TOPIC_LIGHT", "pbl4/nhom3/traffic/light")

    try:
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()
        print(f"[MQTT] Dang lang nghe den tin hieu tai '{broker}:{port}', topic: '{topic}'")
    except Exception as e:
        print(f"[MQTT Warning] Khong the ket noi toi Broker {broker}: {e}. Dung che do doc lap.")

    return client

def send_violation_to_backend(frame, viol_type, veh_type, conf, camera_id=1):
    """
    Gửi dữ liệu vi phạm sang Backend Spring Boot (khớp 100% ViolationCreateDTO)
    - viol_type: "RED_LIGHT_CROSS" hoặc "NO_HELMET"
    - veh_type: "CAR", "MOTORCYCLE", "BUS", "TRUCK"
    - conf: Độ tin cậy (0.85 -> 0.99)
    """
    # 1. Mã hóa ảnh hiện tại sang Base64
    _, buffer = cv2.imencode('.jpg', frame)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

    # 2. Tạo JSON Payload chuẩn ViolationCreateDTO của Backend
    payload = {
        "cameraId": camera_id,
        "violationType": viol_type,
        "vehicleType": veh_type.upper(),
        "confidence": round(float(conf), 2),
        "imageBase64": b64_str
    }

    url = getattr(config, "VIOLATION_ENDPOINT", "http://localhost:8080/api/violations")

    try:
        res = requests.post(url, json=payload, timeout=2)
        if res.status_code in [200, 201]:
            print(f"✅ [AI -> BACKEND] Báo cáo vi phạm thành công lên Server: ID #{res.json().get('id')}")
        else:
            print(f"⚠️ [AI -> BACKEND] Phản hồi HTTP {res.status_code}: {res.text}")
    except requests.exceptions.ConnectionError:
        print(f"ℹ️ [AI -> BACKEND] Backend chưa bật (localhost:8080). Đã ghi nhận vi phạm thành công trên AI!")
    except Exception as e:
        print(f"⚠️ [AI -> BACKEND] Lỗi gửi API: {e}")


# Lưu danh sách ID các xe đã vi phạm đèn đỏ để giữ hộp màu đỏ vĩnh viễn trên màn hình
violating_vehicles = set()

def check_red_light_violation(tracker_id, prev_bottom_y, curr_bottom_y, frame, class_name, conf, stop_line_y=None):
    """
    Kiểm tra xe có vượt qua vạch dừng khi đèn ĐỎ hay không:
    - Áp dụng cơ chế Vùng Vạch Dừng (Stop Zone 50px) chống sót xe nhảy frame.
    - Giữ trạng thái vi phạm vĩnh viễn cho đến khi xe chạy khuất màn hình.
    """
    global current_traffic_light, reported_violations, violating_vehicles

    if stop_line_y is None:
        stop_line_y = getattr(config, "STOP_LINE_Y", 468)

    # 1. Nếu xe này đã từng bị phát hiện vượt đèn đỏ -> Giữ nguyên hộp đỏ vĩnh viễn
    if tracker_id in violating_vehicles:
        return True

    # 2. Vùng Vạch Dừng nhạy bén (dày 50px: từ stop_line_y - 25 đến stop_line_y + 25)
    zone_top = stop_line_y - 25
    zone_bottom = stop_line_y + 25

    crossed_down = (prev_bottom_y <= stop_line_y and curr_bottom_y > stop_line_y)
    crossed_up = (prev_bottom_y >= stop_line_y and curr_bottom_y < stop_line_y)
    in_zone = (zone_top <= curr_bottom_y <= zone_bottom and curr_bottom_y < prev_bottom_y)

    if (crossed_down or crossed_up or in_zone):
        # 3. Chỉ phạt khi đèn đang ĐỎ
        if current_traffic_light == "RED":
            violating_vehicles.add(tracker_id)
            reported_violations[tracker_id] = time.time()
            print(f"\n🚨 [AI PHÁT HIỆN VI PHẠM] Xe #{tracker_id} ({class_name.upper()}) VƯỢT ĐÈN ĐỎ tại vạch Y={stop_line_y}!")
            
            veh_type = "CAR" if class_name in ["car", "bus", "truck"] else "MOTORCYCLE"
            send_violation_to_backend(frame, "RED_LIGHT_CROSS", veh_type, conf)
            return True

    return False


