#include <WiFi.h>
#include <PubSubClient.h>

// ===== CẤU HÌNH WIFI & MQTT =====
const char* ssid = "KHOA DEN";        // Thay bằng tên WiFi nhà bạn
const char* password = "55555555";    // Mật khẩu WiFi
const char* mqtt_server = "192.168.1.10";  // Địa chỉ IP của máy tính chạy Mosquitto Broker (gõ ipconfig xem)
const int mqtt_port = 1883;

// ===== ĐỊNH NGHĨA CHÂN GPIO =====
#define PIN_RED 25
#define PIN_YELLOW 26
#define PIN_GREEN 27
#define PIN_BUZZER 14

WiFiClient espClient;
PubSubClient client(espClient);

// Biến quản lý thời gian chu kỳ đèn (mô phỏng đèn giao thông ngã tư)
unsigned long previousMillis = 0;
int lightState = 0; // 0: ĐỎ (15s), 1: XANH (15s), 2: VÀNG (3s)

void setLights(bool red, bool yellow, bool green) {
    digitalWrite(PIN_RED, red ? HIGH : LOW);
    digitalWrite(PIN_YELLOW, yellow ? HIGH : LOW);
    digitalWrite(PIN_GREEN, green ? HIGH : LOW);
}

// Hàm nhận tin nhắn từ Mosquitto Broker (Topic: traffic/alert)
void callback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.println(" [MQTT ALERT] Nhận lệnh cảnh báo từ Backend: " + message);

    // KHI CÓ XE VI PHẠM: Kích hoạt còi kêu BÍP BÍP 3 lần và nháy đèn đỏ
    for (int i = 0; i < 3; i++) {
        digitalWrite(PIN_BUZZER, HIGH);
        digitalWrite(PIN_RED, HIGH);
        delay(150);
        digitalWrite(PIN_BUZZER, LOW);
        digitalWrite(PIN_RED, LOW);
        delay(150);
    }

    // Khôi phục lại trạng thái đèn trước đó
    if (lightState == 0) setLights(true, false, false);
    else if (lightState == 1) setLights(false, false, true);
    else setLights(false, true, false);
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_RED, OUTPUT);
    pinMode(PIN_YELLOW, OUTPUT);
    pinMode(PIN_GREEN, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);

    // Mặc định bật đèn đỏ ban đầu
    setLights(true, false, false);

    // Kết nối WiFi
    Serial.print("Đang kết nối WiFi: ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi đã kết nối thành công! IP ESP32: " + WiFi.localIP().toString());

    // Cấu hình MQTT Broker
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Đang kết nối Mosquitto MQTT Broker...");
        if (client.connect("ESP32_TrafficMonitor")) {
            Serial.println(" ĐÃ KẾT NỐI!");
            // Đăng ký nhận thông điệp cảnh báo vi phạm
            client.subscribe("traffic/alert");
            Serial.println("Đã subscribe topic: traffic/alert");
        } else {
            Serial.print("Thất bại, mã lỗi rc=");
            Serial.print(client.state());
            Serial.println(" -> Thử lại sau 5 giây");
            delay(5000);
        }
    }
}

void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    // VÒNG LẶP CHUYỂN ĐÈN TỰ ĐỘNG THEO THỜI GIAN
    unsigned long currentMillis = millis();
    
    // Đèn Đỏ: 15 giây
    if (lightState == 0 && currentMillis - previousMillis >= 15000) {
        previousMillis = currentMillis;
        lightState = 1; // Chuyển sang Xanh
        setLights(false, false, true);
        client.publish("traffic/light", "GREEN");
        Serial.println(" Đèn chuyển sang: XANH");
    }
    // Đèn Xanh: 15 giây
    else if (lightState == 1 && currentMillis - previousMillis >= 15000) {
        previousMillis = currentMillis;
        lightState = 2; // Chuyển sang Vàng
        setLights(false, true, false);
        client.publish("traffic/light", "YELLOW");
        Serial.println(" Đèn chuyển sang: VÀNG");
    }
    // Đèn Vàng: 3 giây
    else if (lightState == 2 && currentMillis - previousMillis >= 3000) {
        previousMillis = currentMillis;
        lightState = 0; // Chuyển sang Đỏ
        setLights(true, false, false);
        client.publish("traffic/light", "RED");
        Serial.println(" Đèn chuyển sang: ĐỎ");
    }
}