"""
==============================================================================
 ĐỒ ÁN PBL4 - HỆ THỐNG GIÁM SÁT GIAO THÔNG THÔNG MINH (NHÓM 3)
 SCRIPT GIẢ LẬP ESP32 CHẠY TRÊN MÁY TÍNH (KÈM TIẾNG BÍP CÒI HÚ WINDOWS)
 Chạy: python hardware/fake_esp32.py
==============================================================================
"""
import paho.mqtt.client as mqtt
import time
import json
import threading
import sys

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# Broker Cloud & Topics khớp 100% Backend & ESP32 thật
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_ALERT = "pbl4/nhom3/traffic/alert"
TOPIC_LIGHT = "pbl4/nhom3/traffic/light"

def play_buzzer():
    """Giả lập tiếng còi hú Active Buzzer trên loa máy tính"""
    if HAS_SOUND:
        for _ in range(4):
            winsound.Beep(1500, 150)
            time.sleep(0.08)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"\n✅ [FAKE ESP32] Đã kết nối thành công tới Mosquitto Broker ({BROKER}:1883)!")
        client.subscribe(TOPIC_ALERT)
        client.subscribe("traffic/alert")
        print(f"👂 Đang lắng nghe kênh cảnh báo còi hú: {TOPIC_ALERT}")
        print("🚦 Bắt đầu tự động phát chu kỳ đèn giao thông (Đỏ 15s -> Xanh 15s -> Vàng 3s)...\n")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

def on_message(client, userdata, msg):
    content = msg.payload.decode('utf-8', errors='ignore')
    print("\n" + "!" * 65)
    print(f"🚨 [CÒI HÚ HIỆN TRƯỜNG] Nhận lệnh từ: {msg.topic}")
    print(f"📋 Nội dung cảnh báo: {content}")
    print(">>> 🔊 CÒI ACTIVE BUZZER ĐANG HÚ VANG: BÍP... BÍP... BÍP... <<<")
    print(">>> 🔴 ĐÈN ĐỎ CHỚP NHÁY LIÊN TỤC TẠI NGÃ TƯ <<<")
    print("!" * 65 + "\n")
    
    # Kêu bíp trên loa máy tính
    threading.Thread(target=play_buzzer, daemon=True).start()

def light_cycle_publisher(client):
    """Phát trạng thái chu kỳ đèn lên MQTT để AI và Backend đồng bộ"""
    phases = [("RED", 15), ("GREEN", 15), ("YELLOW", 3)]
    time.sleep(2)
    while True:
        for status, duration in phases:
            for remaining in range(duration, 0, -1):
                payload = json.dumps({
                    "status": status,
                    "remainingSeconds": remaining,
                    "cycleDuration": 33,
                    "cameraId": 1
                })
                try:
                    client.publish(TOPIC_LIGHT, payload)
                except Exception:
                    pass
                time.sleep(1)

def main():
    print("=" * 65)
    print("🚦 ESP32 SIMULATOR - TRAFFIC LIGHT & BUZZER ALARM (PBL4) 🚦")
    print("=" * 65)
    print(f"🌐 Đang kết nối tới Cloud Broker: {BROKER}:{PORT} ...")

    client = mqtt.Client(client_id="PBL4_Fake_ESP32_Simulator")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
    except Exception as e:
        print(f"⚠️ Không thể kết nối tới {BROKER}: {e}. Đang thử kết nối localhost...")
        client.connect("localhost", PORT, 60)

    # Chạy thread phát chu kỳ đèn
    pub_thread = threading.Thread(target=light_cycle_publisher, args=(client,), daemon=True)
    pub_thread.start()

    # Lắng nghe nhận lệnh còi hú
    client.loop_forever()

if __name__ == "__main__":
    main()