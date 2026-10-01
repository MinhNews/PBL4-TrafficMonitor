import os, sys, cv2, json, base64, requests, time
import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

# Trạng thái đèn tín hiệu hiện tại (mặc định là GREEN)
current_traffic_light = "GREEN"

# Theo dõi kết nối phần cứng ESP32 thật
last_esp32_heartbeat = 0
esp32_remaining_seconds = None

def is_esp32_online():
    """Kiểm tra xem bo mạch ESP32 thật có đang phát tín hiệu qua MQTT hay không"""
    global last_esp32_heartbeat
    # ESP32 thật gửi mỗi 1 giây. Nếu trong vòng 4 giây có nhận được tin nhắn thì là ONLINE
    return (time.time() - last_esp32_heartbeat) < 4.0

def set_manual_light(new_light):
    """
    CHỈ DÙNG KHI TEST TẠI NHÀ (VẮNG BO PHẦN CỨNG ESP32).
    Khi có bo ESP32 thật hoạt động, hệ thống TUYỆT ĐỐI KHÓA can thiệp thủ công để bảo toàn tín hiệu thật ngoài hiện trường!
    """
    global current_traffic_light
    if is_esp32_online():
        print(f"🔒 [BẢO VỆ PHẦN CỨNG] Bo ESP32 thật đang hoạt động ngoài ngã tư! Từ chối can thiệp thủ công để đảm bảo tính xác thực.")
        return False
    current_traffic_light = new_light
    print(f"🛠️ [TEST NỘI BỘ TẠI NHÀ] Đã đổi đèn sang {new_light} (Chỉ áp dụng khi vắng bo ESP32)")
    return True

# Lưu lịch sử vi phạm để không gửi trùng lặp nhiều lần cho cùng 1 xe: {tracker_id: timestamp_violation}
reported_violations = {}

def on_mqtt_message(client, userdata, msg):
    """Lắng nghe trạng thái đèn tín hiệu thời gian thực từ bo ESP32 thật qua MQTT"""
    global current_traffic_light, last_esp32_heartbeat, esp32_remaining_seconds

    # Ghi nhận nhịp đập tín hiệu từ phần cứng thật (Heartbeat)
    last_esp32_heartbeat = time.time()

    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        if isinstance(data, dict):
            new_status = (data.get("status") or data.get("light") or "GREEN").upper()
            if new_status in ["RED", "YELLOW", "GREEN"]:
                current_traffic_light = new_status
            esp32_remaining_seconds = data.get("remainingSeconds")
            print(f"🚦 [TÍN HIỆU TỪ ESP32] Đèn: {current_traffic_light} | Đếm ngược: {esp32_remaining_seconds}s")
        else:
            txt = str(data).upper()
            if txt in ["RED", "YELLOW", "GREEN"]:
                current_traffic_light = txt
            print(f"🚦 [TÍN HIỆU TỪ ESP32] Đèn: {current_traffic_light}")
    except Exception:
        text = msg.payload.decode('utf-8').strip().strip('"').upper()
        if text in ["RED", "YELLOW", "GREEN"]:
            current_traffic_light = text
            print(f"🚦 [TÍN HIỆU TỪ ESP32] Đèn: {current_traffic_light}")

def _connect_mqtt_thread(client, broker, port, topic):
    def _on_connect(cl, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"✅ [MQTT] Đã kết nối Broker '{broker}:{port}'! Đang subscribe '{topic}'...")
            cl.subscribe(topic)
        else:
            print(f"❌ [MQTT Warning] Kết nối Broker thất bại, rc={rc}")

    client.on_connect = _on_connect
    try:
        client.connect(broker, port, keepalive=30)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT Warning] Không thể kết nối tới Broker {broker}: {e}. Dùng chế độ độc lập.")

def start_light_listener():
    """Khởi chạy luồng ngầm lắng nghe trạng thái đèn giao thông"""
    unique_id = f"AI_Light_{int(time.time())}_{os.getpid()}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None, client_id=unique_id)
    client.on_message = on_mqtt_message

    broker = getattr(config, "MQTT_BROKER", "test.mosquitto.org")
    port = getattr(config, "MQTT_PORT", 1883)
    topic = getattr(config, "MQTT_TOPIC_LIGHT", "pbl4/nhom3/traffic/light")

    t = threading.Thread(target=_connect_mqtt_thread, args=(client, broker, port, topic), daemon=True)
    t.start()
    return client

import threading

def _async_post(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            data = res.json()
            print(f"\n✅ [AI -> BACKEND] Đã báo cáo vi phạm lên Server thành công! ID #{data.get('id')} | Mức phạt: {data.get('fineAmount')}")
        else:
            print(f"\n⚠️ [AI -> BACKEND] Phản hồi HTTP {res.status_code}: {res.text}")
    except requests.exceptions.ConnectionError:
        print(f"\nℹ️ [AI -> BACKEND] Backend chưa bật (localhost:8080). Đã ghi nhận vi phạm thành công trên AI!")
    except Exception as e:
        print(f"\n⚠️ [AI -> BACKEND] Lỗi gửi API: {e}")

def send_violation_to_backend(frame, viol_type, veh_type, conf, camera_id=1):
    """
    Gửi dữ liệu vi phạm sang Backend Spring Boot qua luồng ngầm (Asynchronous):
    - KHÔNG làm chậm hoặc giật video (30 FPS mượt mà)
    - Timeout 10s đủ để Backend đẩy ảnh lên Cloudinary
    """
    frame_copy = frame.copy()
    _, buffer = cv2.imencode('.jpg', frame_copy)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

    payload = {
        "cameraId": camera_id,
        "violationType": viol_type,
        "vehicleType": veh_type.upper(),
        "confidence": round(float(conf), 2),
        "imageBase64": b64_str
    }

    url = getattr(config, "VIOLATION_ENDPOINT", "http://localhost:8080/api/violations")
    threading.Thread(target=_async_post, args=(url, payload), daemon=True).start()


# Lưu danh sách ID các xe đã vi phạm đèn đỏ để giữ hộp màu đỏ vĩnh viễn trên màn hình
violating_vehicles = set()
passed_vehicles = set()

def send_traffic_flow_to_backend(count=1, vehicle_type="car", camera_id=1):
    """Gửi số lượt phương tiện lưu thông thực tế về Backend Spring Boot"""
    payload = {
        "cameraId": camera_id,
        "count": count,
        "vehicleType": vehicle_type
    }
    url = "http://localhost:8080/api/stats/flow"
    threading.Thread(target=_async_post_flow, args=(url, payload), daemon=True).start()

def _async_post_flow(url, payload):
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass

def check_traffic_flow(tracker_id, prev_bottom_y, curr_bottom_y, class_name, stop_line_y=None):
    """
    Đếm lưu lượng phương tiện thực tế khi xe cắt qua vạch ngã tư
    """
    global passed_vehicles
    if tracker_id in passed_vehicles:
        return False

    if stop_line_y is None:
        stop_line_y = getattr(config, "STOP_LINE_Y", 468)

    zone_top = stop_line_y - 30
    zone_bottom = stop_line_y + 30

    crossed = (prev_bottom_y <= stop_line_y and curr_bottom_y > stop_line_y) or \
              (prev_bottom_y >= stop_line_y and curr_bottom_y < stop_line_y) or \
              (zone_top <= curr_bottom_y <= zone_bottom)

    if crossed:
        passed_vehicles.add(tracker_id)
        veh_type = "car" if class_name in ["car", "bus", "truck"] else "motorcycle"
        send_traffic_flow_to_backend(count=1, vehicle_type=veh_type)
        print(f"📊 [LƯU LƯỢNG XE THẬT] Xe #{tracker_id} ({veh_type.upper()}) vừa qua nút giao. Tổng hôm nay: {len(passed_vehicles)}")
        return True

    return False

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



