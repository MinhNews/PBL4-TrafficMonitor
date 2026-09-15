#!/usr/bin/env python3
"""
fake_esp32.py
Giả lập ESP32 trên máy tính - Test MQTT không cần phần cứng thật.
Chạy: python fake_esp32.py
"""

import paho.mqtt.client as mqtt
import json
import time

# CẤU HÌNH 
BROKER = "localhost"
PORT   = 1883

TOPIC_ALERT = "traffic/alert"
TOPIC_LIGHT = "traffic/light"

# TRẠNG THÁI ĐÈN
light_order = ["GREEN", "YELLOW", "RED"]
light_times = {"GREEN": 15, "YELLOW": 3, "RED": 15}

state = {
    "idx": 0,
    "remaining": light_times["GREEN"]
}

#CALLBACKS 
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(" fake_esp32 kết nối MQTT thành công!")
        client.subscribe(TOPIC_ALERT)
        print(f" Subscribe: {TOPIC_ALERT}")
        print(f" Publish đến: {TOPIC_LIGHT}")
        print("=" * 55)
    else:
        print(f"Kết nối thất bại! Mosquitto đã chạy chưa? rc={rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"\n Nhận cảnh báo từ [{msg.topic}]: {payload}")
    try:
        data = json.loads(payload)
        vtype = data.get("type", "UNKNOWN")
        beeps = data.get("beepTimes", 3)
        print(f" Loại vi phạm: {vtype}")
        print(f" BÍP! " * beeps)
        print(" Đèn đỏ nháy 3 lần!")
        print("=" * 55)
    except Exception as e:
        print(f" JSON lỗi: {e}")

#MAIN 
def main():
    client = mqtt.Client(client_id="fake-esp32")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
    except Exception as e:
        print(f" Không kết nối được broker {BROKER}:{PORT}")
        print(f"   Chi tiết: {e}")
        print("   → Nhớ chạy lệnh: mosquitto -v")
        return

    client.loop_start()
    print(" fake_esp32 đang chạy... (Ctrl+C để thoát)\n")

    last_tick = time.time()

    try:
        while True:
            now = time.time()
            if now - last_tick >= 1:
                last_tick = now
                state["remaining"] -= 1

                # Publish trạng thái đèn mỗi giây
                status = light_order[state["idx"]]
                payload = json.dumps({
                    "status": status,
                    "remainingSeconds": state["remaining"]
                })
                client.publish(TOPIC_LIGHT, payload)

                # Chuyển đèn
                if state["remaining"] <= 0:
                    state["idx"] = (state["idx"] + 1) % 3
                    status = light_order[state["idx"]]
                    state["remaining"] = light_times[status]
                    print(f" Đèn: {status} ({state['remaining']}s)")

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n Dừng fake_esp32.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()