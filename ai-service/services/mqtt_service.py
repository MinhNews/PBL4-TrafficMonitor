import os, sys, json, time, threading
import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

class MqttTrafficLightService:
    """
    Dịch vụ lắng nghe trạng thái Đèn Giao Thông từ bo mạch ESP32 thật qua MQTT.
    - Lắng nghe topic: pbl4/nhom3/traffic/light
    - Cơ chế Heartbeat phát hiện ESP32 thật online
    - Khóa an toàn phần cứng (Hardware-Lock Safety): Từ chối can thiệp thủ công khi mạch thật đang chạy
    - Cho phép test chuyển đèn thủ công khi vắng bo mạch thật
    """
    def __init__(self):
        self.current_light = "GREEN"
        self.last_heartbeat = 0
        self.remaining_seconds = None
        self.client = None

    def is_esp32_online(self):
        """ESP32 thật gửi mỗi 1 giây. Nếu trong vòng 4s có nhận được tin nhắn thì là ONLINE"""
        return (time.time() - self.last_heartbeat) < 4.0

    def set_manual_light(self, new_light):
        """Chuyển đèn thủ công khi test tại nhà vắng bo phần cứng ESP32"""
        if self.is_esp32_online():
            print("🔒 [BẢO VỆ PHẦN CỨNG] Bo ESP32 thật đang hoạt động! Khóa can thiệp thủ công để đảm bảo tính xác thực.")
            return False
        light = str(new_light).upper()
        if light in ["RED", "YELLOW", "GREEN"]:
            self.current_light = light
            print(f"🛠️ [TEST NỘI BỘ] Đã đổi đèn sang {light} (Chỉ áp dụng khi vắng bo ESP32)")
            return True
        return False

    def reset_to_auto(self):
        """Khôi phục chế độ tự động nhận diện từ ESP32"""
        print("🔄 [CHUYỂN ĐỔI] Đã bật chế độ tự động nhận diện theo ESP32 / MQTT.")
        return True

    def _on_message(self, client, userdata, msg):
        self.last_heartbeat = time.time()
        try:
            payload_str = msg.payload.decode('utf-8')
            data = json.loads(payload_str)
            if isinstance(data, dict):
                new_status = (data.get("status") or data.get("light") or "GREEN").upper()
                if new_status in ["RED", "YELLOW", "GREEN"]:
                    self.current_light = new_status
                self.remaining_seconds = data.get("remainingSeconds")
                print(f"🚦 [TÍN HIỆU TỪ ESP32] Đèn: {self.current_light} | Đếm ngược: {self.remaining_seconds}s")
            else:
                txt = str(data).upper()
                if txt in ["RED", "YELLOW", "GREEN"]:
                    self.current_light = txt
        except Exception:
            text = msg.payload.decode('utf-8').strip().strip('"').upper()
            if text in ["RED", "YELLOW", "GREEN"]:
                self.current_light = text

    def start(self):
        """Khởi động luồng ngầm kết nối Broker MQTT"""
        unique_id = f"TrafficMonitor_AI_{int(time.time())}_{os.getpid()}"
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None,
            client_id=unique_id
        )
        self.client.on_message = self._on_message

        broker = getattr(config, "MQTT_BROKER", "test.mosquitto.org")
        port = getattr(config, "MQTT_PORT", 1883)
        topic = getattr(config, "MQTT_TOPIC_LIGHT", "pbl4/nhom3/traffic/light")

        def _connect():
            def _on_connect(cl, ud, flags, rc, properties=None):
                if rc == 0:
                    print(f"✅ [MQTT] Đã kết nối Broker '{broker}:{port}'! Đang theo dõi topic: '{topic}'")
                    cl.subscribe(topic)
                else:
                    print(f"❌ [MQTT] Kết nối thất bại, rc={rc}")
            self.client.on_connect = _on_connect
            try:
                self.client.connect(broker, port, keepalive=30)
                self.client.loop_start()
            except Exception as e:
                print(f"[MQTT Warning] Không thể kết nối tới Broker {broker}: {e}. Dùng chế độ độc lập.")

        t = threading.Thread(target=_connect, daemon=True)
        t.start()
        return self

    def stop(self):
        if self.client:
            try:
                self.client.loop_stop()
            except Exception:
                pass
