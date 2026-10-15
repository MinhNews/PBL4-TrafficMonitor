import os, sys, cv2, json, base64, requests, time, threading
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

def reset_to_auto_esp32():
    """Khôi phục lại chế độ tự động nhận diện tín hiệu từ ESP32"""
    global current_traffic_light
    print("🔄 [CHUYỂN ĐỔI] Đã bật chế độ tự động nhận diện theo ESP32 / MQTT.")
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
        res = requests.post(url, json=payload, timeout=25)
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


# Lưu danh sách ID các xe đã vi phạm đèn đỏ kèm tọa độ box: {tracker_id: {"timestamp": float, "box": list}}
violating_vehicles = {}
passed_vehicles = set()

def reset_tracking_state():
    """Xóa sạch bộ nhớ vi phạm và lưu lượng khi tua lại video (loop) hoặc đổi camera"""
    global violating_vehicles, passed_vehicles, reported_violations
    violating_vehicles.clear()
    passed_vehicles.clear()
    reported_violations.clear()
    print("🔄 [RESET BỘ NHỚ] Đã làm mới toàn bộ danh sách vi phạm & lưu lượng xe cho chu kỳ mới.")

def _box_iou(boxA, boxB):
    """Tính độ trùng lặp IoU giữa 2 bounding box"""
    if boxA is None or boxB is None or len(boxA) < 4 or len(boxB) < 4:
        return 0.0
    xa = max(boxA[0], boxB[0])
    ya = max(boxA[1], boxB[1])
    xb = min(boxA[2], boxB[2])
    yb = min(boxA[3], boxB[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    areaA = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    areaB = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union = areaA + areaB - inter
    return inter / max(1.0, union)

def check_line_crossing(prev_y, curr_y, stop_line_y):
    """
    Kiểm tra mép trước (đầu xe) cắt qua vạch dừng theo cả 2 chiều:
    - Chiều đi lên (Y giảm - từ đáy lên ngã tư như traffic2.mp4): prev_y >= stop_line_y và curr_y < stop_line_y
    - Chiều đi xuống (Y tăng - từ ngã tư xuống phía dưới): prev_y <= stop_line_y và curr_y > stop_line_y
    """
    if prev_y is None or curr_y is None:
        return False
    crossed_up = (prev_y >= stop_line_y and curr_y < stop_line_y)
    crossed_down = (prev_y <= stop_line_y and curr_y > stop_line_y)
    return crossed_up or crossed_down

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

def check_traffic_flow(tracker_id, prev_front_y, curr_front_y, class_name, stop_line_y=None):
    """
    Đếm lưu lượng phương tiện cơ giới thực tế khi đầu xe cắt qua vạch ngã tư
    """
    global passed_vehicles
    TRAFFIC_CLASSES = {"car", "motorcycle", "bus", "truck", "person", "rider"}
    if class_name not in TRAFFIC_CLASSES:
        return False

    if tracker_id in passed_vehicles:
        return False

    if stop_line_y is None:
        stop_line_y = getattr(config, "STOP_LINE_Y", 468)

    crossed = check_line_crossing(prev_front_y, curr_front_y, stop_line_y)

    if crossed:
        passed_vehicles.add(tracker_id)
        veh_type = "car" if class_name in ["car", "bus", "truck"] else "motorcycle"
        send_traffic_flow_to_backend(count=1, vehicle_type=veh_type)
        print(f"📊 [LƯU LƯỢNG XE] Xe #{tracker_id} ({veh_type.upper()}) qua ngã tư. Tổng: {len(passed_vehicles)}")
        return True

    return False

def check_red_light_violation(tracker_id, prev_front_y, curr_front_y, frame, class_name, conf, stop_line_y=None, box=None):
    """
    Kiểm tra xe cơ giới (ô tô, xe máy, xe tải, người lái xe) vượt đèn đỏ theo mép đầu xe.
    Tạo ảnh bằng chứng sạch (clean evidence) gửi lên Backend.
    """
    global current_traffic_light, reported_violations, violating_vehicles

    TRAFFIC_CLASSES = {"car", "motorcycle", "bus", "truck", "person", "rider"}
    if class_name not in TRAFFIC_CLASSES:
        return False

    if stop_line_y is None:
        stop_line_y = getattr(config, "STOP_LINE_Y", 468)

    now = time.time()

    # 1. Nếu xe này đã được xác nhận vi phạm: tiếp tục duy trì trạng thái (chống nhấp nháy 100%)
    if tracker_id in violating_vehicles:
        violating_vehicles[tracker_id]["timestamp"] = now
        if box is not None:
            violating_vehicles[tracker_id]["box"] = box
        return True

    # 2. Cơ chế Kế thừa vi phạm: Nếu ByteTrack đổi tracker_id khi xe đang vượt, đối chiếu IoU với xe vừa vi phạm
    if box is not None:
        for v_id, v_data in list(violating_vehicles.items()):
            if (now - v_data["timestamp"]) < 6.0: # Trong vòng 6s từ lúc vượt
                if _box_iou(box, v_data["box"]) > 0.35:
                    violating_vehicles[tracker_id] = {"timestamp": now, "box": box}
                    return True

    # 3. Kiểm tra mép đầu xe cắt qua vạch dừng khi đèn ĐỎ
    crossed = check_line_crossing(prev_front_y, curr_front_y, stop_line_y)

    if crossed and current_traffic_light == "RED":
        violating_vehicles[tracker_id] = {"timestamp": now, "box": box or [0, 0, 0, 0]}
        reported_violations[tracker_id] = now
        veh_type = "CAR" if class_name in ["car", "bus", "truck"] else "MOTORCYCLE"
        print(f"\n🚨 [AI PHÁT HIỆN VI PHẠM] Xe #{tracker_id} ({veh_type}) VƯỢT ĐÈN ĐỎ tại vạch Y={stop_line_y}!")

        # Tạo ảnh bằng chứng sạch chỉ khoanh khung đỏ quanh xe vi phạm
        evidence = frame.copy()
        if box is not None:
            bx1, by1, bx2, by2 = map(int, box)
            cv2.rectangle(evidence, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
            cv2.putText(evidence, f"VUOT DEN DO #{tracker_id}", (bx1, max(20, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        send_violation_to_backend(evidence, "RED_LIGHT_CROSS", veh_type, conf)
        return True

    return False



