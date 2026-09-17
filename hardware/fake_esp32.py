"""
Script giả lập ESP32 chạy trên máy tính:
python hardware/fake_esp32.py
"""
import paho.mqtt.client as mqtt
import time

BROKER = "localhost"
PORT = 1883
TOPIC_ALERT = "traffic/alert"
TOPIC_LIGHT = "traffic/light"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(" [FAKE ESP32] Đã kết nối thành công tới Mosquitto Broker!")
        client.subscribe(TOPIC_ALERT)
        print(f" Đã subscribe topic: {TOPIC_ALERT}")
    else:
        print(f" Kết nối thất bại, mã lỗi: {rc}")

def on_message(client, userdata, msg):
    content = msg.payload.decode('utf-8')
    print(f" [CẢNH BÁO VI PHẠM] Nhận lệnh từ: {msg.topic} | Nội dung: {content}")
    print(" >>> CÒI ACTIVE BUZZER KÊU: BÍP... BÍP... BÍP... <<<")
    print(" >>> ĐÈN ĐỎ NHẤP NHÁY CẢNH BÁO XE VI PHẠM <<<\n")

client = mqtt.Client(client_id="Fake_ESP32_Client")
client.on_connect = on_connect
client.on_message = on_message

print(" Đang kết nối tới Mosquitto Broker localhost:1883...")
client.connect(BROKER, PORT, 60)

# Chạy vòng lặp lắng nghe
client.loop_forever()