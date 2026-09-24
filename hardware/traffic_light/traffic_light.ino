// hardware/traffic_light/traffic_light_esp32.ino
/*
 ==============================================================================
  ĐỒ ÁN PBL4 - HỆ THỐNG GIÁM SÁT GIAO THÔNG THÔNG MINH (NHÓM 3 - ĐH BÁCH KHOA ĐN)
  MÃ NGUỒN NẠP VÀO BO MẠCH THẬT ESP32 DEVKIT V1 (ARDUINO IDE)
  Thành viên phụ trách: Phan Quang Đăng Khoa (Hardware & IoT)
 ==============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// ===== CẤU HÌNH MÀN HÌNH OLED 0.96 INCH SSD1306 (I2C) =====
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ===== ĐỊNH NGHĨA CHÂN GPIO THỰC TẾ TRÊN BO ESP32 =====
const int PIN_RED    = 25;  // LED Đỏ ngã tư
const int PIN_YELLOW = 26;  // LED Vàng
const int PIN_GREEN  = 27;  // LED Xanh
const int PIN_BUZZER = 14;  // Còi báo động Active Buzzer 5V

// ===== CẤU HÌNH KẾT NỐI WIFI THẬT =====
// 👉 KHOA ĐIỀN TÊN VÀ MẬT KHẨU WIFI CỦA BẠN VÀO ĐÂY:
const char* WIFI_SSID = "YOUR_WIFI_NAME";        // Tên WiFi (hoặc Hotspot điện thoại)
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";    // Mật khẩu WiFi

// ===== CẤU HÌNH MQTT BROKER =====
// Dùng Cloud Broker để ESP32 ở bất cứ đâu có WiFi đều nói chuyện được với Backend:
const char* MQTT_SERVER = "test.mosquitto.org";
const int   MQTT_PORT   = 1883;

// Topics trao đổi thông tin với Backend Spring Boot & AI
const char* TOPIC_LIGHT = "pbl4/nhom3/traffic/light";
const char* TOPIC_ALERT = "pbl4/nhom3/traffic/alert";

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastTick = 0;
int lightPhase = 0;   // 0: ĐỎ, 1: XANH, 2: VÀNG
int secondsLeft = 15; // Đỏ 15s -> Xanh 15s -> Vàng 3s

// ===== HÀM CẬP NHẬT GIAO DIỆN MÀN HÌNH OLED SSD1306 =====
void updateOLED(const char* state, int remaining, bool isAlert = false) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    
    // Header tiêu đề hệ thống
    display.setTextSize(1);
    display.setCursor(10, 0);
    display.print("PBL4 - TRAFFIC IOT");
    display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

    if (isAlert) {
        // Màn hình cảnh báo khẩn cấp khi Backend phát hiện vi phạm
        display.setTextSize(2);
        display.setCursor(4, 18);
        display.print("!CANH BAO!");
        display.setTextSize(1);
        display.setCursor(6, 42);
        display.print("PHAT HIEN VI PHAM");
        display.setCursor(12, 53);
        display.print("COI HU HIEN TRUONG");
    } else {
        // Màn hình hiển thị trạng thái đèn và số giây đếm ngược
        display.setTextSize(2);
        display.setCursor(16, 18);
        display.print(state);

        display.setTextSize(3);
        display.setCursor(46, 38);
        if (remaining < 10) display.print("0");
        display.print(remaining);
    }
    display.display();
}

// ===== HÀM KÍCH HOẠT CÒI HÚ THẬT & ĐÈN ĐỎ CHỚP NHÁY LIÊN TỤC =====
void triggerHardwareAlarm() {
    Serial.println("\n🚨 [HARDWARE] NHẬN LỆNH CẢNH BÁO TỪ BACKEND!");
    Serial.println(">>> CÒI ACTIVE BUZZER ĐANG HÚ VANG TẠI PHÒNG! <<<");
    updateOLED("ALERT", 0, true);
    
    // Còi kêu 4 tiếng BÍP BÍP dồn dập kèm đèn đỏ chớp tắt
    for (int i = 0; i < 4; i++) {
        digitalWrite(PIN_BUZZER, HIGH); // Còi kêu thật sự!
        digitalWrite(PIN_RED, HIGH);    // Đèn đỏ nhấp nháy!
        delay(140);
        digitalWrite(PIN_BUZZER, LOW);
        digitalWrite(PIN_RED, LOW);
        delay(100);
    }
}

// ===== HÀM NHẬN BẢN TIN MQTT TỪ BACKEND SPRING BOOT =====
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.print("📩 [MQTT NHẬN ĐƯỢC] Kênh: ");
    Serial.print(topic);
    Serial.print(" | Nội dung: ");
    Serial.println(message);

    if (String(topic) == TOPIC_ALERT) {
        triggerHardwareAlarm();
    }
}

// ===== HÀM TỰ ĐỘNG KẾT NỐI LẠI MQTT KHI RỚT MẠNG =====
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("Đang kết nối MQTT Broker (test.mosquitto.org)...");
        String clientId = "ESP32-RealBoard-" + String(random(0xffff), HEX);
        if (client.connect(clientId.c_str())) {
            Serial.println(" ĐÃ KẾT NỐI THÀNH CÔNG!");
            client.subscribe(TOPIC_ALERT);
            Serial.println("👂 Đã đăng ký lắng nghe kênh còi hú: pbl4/nhom3/traffic/alert");
        } else {
            Serial.print(" Thất bại, rc=");
            Serial.print(client.state());
            Serial.println(" -> Thử lại sau 2 giây...");
            delay(2000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    // Cấu hình các chân xuất tín hiệu
    pinMode(PIN_RED, OUTPUT);
    pinMode(PIN_YELLOW, OUTPUT);
    pinMode(PIN_GREEN, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    
    digitalWrite(PIN_RED, LOW);
    digitalWrite(PIN_YELLOW, LOW);
    digitalWrite(PIN_GREEN, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    // Khởi động màn hình OLED qua giao tiếp I2C (địa chỉ 0x3C)
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        Serial.println("❌ Không tìm thấy màn hình OLED SSD1306! Kiểm tra lại chân SDA/SCL.");
    }
    display.clearDisplay();
    display.display();

    // Kết nối vào mạng WiFi thật
    Serial.print("Đang kết nối vào mạng WiFi: ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ WiFi đã kết nối thành công! IP của ESP32: " + WiFi.localIP().toString());

    // Cấu hình MQTT
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setCallback(mqttCallback);
}

void loop() {
    if (!client.connected()) {
        reconnectMQTT();
    }
    client.loop();

    unsigned long now = millis();
    if (now - lastTick >= 1000) {
        lastTick = now;
        secondsLeft--;

        const char* statusStr = "RED";
        if (lightPhase == 0) {
            // PHA ĐÈN ĐỎ (15 GIÂY)
            statusStr = "RED";
            digitalWrite(PIN_RED, HIGH);
            digitalWrite(PIN_YELLOW, LOW);
            digitalWrite(PIN_GREEN, LOW);
            if (secondsLeft <= 0) { lightPhase = 1; secondsLeft = 15; }
        } else if (lightPhase == 1) {
            // PHA ĐÈN XANH (15 GIÂY)
            statusStr = "GREEN";
            digitalWrite(PIN_RED, LOW);
            digitalWrite(PIN_YELLOW, LOW);
            digitalWrite(PIN_GREEN, HIGH);
            if (secondsLeft <= 0) { lightPhase = 2; secondsLeft = 3; }
        } else {
            // PHA ĐÈN VÀNG (3 GIÂY)
            statusStr = "YELLOW";
            digitalWrite(PIN_RED, LOW);
            digitalWrite(PIN_YELLOW, HIGH);
            digitalWrite(PIN_GREEN, LOW);
            if (secondsLeft <= 0) { lightPhase = 0; secondsLeft = 15; }
        }

        // Hiển thị thời gian thực lên màn hình OLED
        updateOLED(statusStr, secondsLeft);

        // Đóng gói JSON gửi trạng thái đèn sang Backend & AI
        StaticJsonDocument<128> doc;
        doc["status"] = statusStr;
        doc["remainingSeconds"] = secondsLeft;
        doc["cycleDuration"] = 33;
        doc["cameraId"] = 1;
        char buffer[128];
        serializeJson(doc, buffer);
        client.publish(TOPIC_LIGHT, buffer);
    }
}