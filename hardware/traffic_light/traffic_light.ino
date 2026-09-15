#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

//CẤU HÌNH
#define WIFI_SSID       "TEN_WIFI_CUA_BAN"
#define WIFI_PASSWORD   "MAT_KHAU_WIFI"

#define MQTT_SERVER     "192.168.1.100"  // IP máy tính chạy Mosquitto
#define MQTT_PORT       1883
#define MQTT_CLIENT_ID  "esp32-traffic-light"

#define TOPIC_ALERT     "traffic/alert"
#define TOPIC_LIGHT     "traffic/light"

//CHÂN GPIO
#define LED_RED     25
#define LED_YELLOW  26
#define LED_GREEN   27
#define BUZZER      14

//TRẠNG THÁI ĐÈN
// 0 = ĐỎ, 1 = VÀNG, 2 = XANH
int lightState = 2;      // bắt đầu bằng XANH
int countdown = 15;
unsigned long lastTick = 0;

// Thời gian đèn (giây)
const int TIME_RED    = 15;
const int TIME_YELLOW = 3;
const int TIME_GREEN  = 15;

WiFiClient espClient;
PubSubClient mqttClient(espClient);

//HÀM ĐIỀU KHIỂN ĐÈN
void setLight(int state) {
  digitalWrite(LED_RED,    state == 0 ? HIGH : LOW);
  digitalWrite(LED_YELLOW, state == 1 ? HIGH : LOW);
  digitalWrite(LED_GREEN,  state == 2 ? HIGH : LOW);
}
// chuyển đèn 
const char* lightName(int state) {
  if (state == 0) return "RED";
  if (state == 1) return "YELLOW";
  return "GREEN";
}

//HÀM BÍP CÒI
void beep(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(150);
    digitalWrite(BUZZER, LOW);
    delay(100);
  }
}

//CALLBACK KHI NHẬN MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  //gom dữ liệu nhận được thành một chuỗi String 
  Serial.println(" MQTT nhận [" + String(topic) + "]: " + msg);

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, msg);
  //đọc chuỗi JSON
  if (err) {
    Serial.println(" JSON lỗi: " + String(err.c_str()));
    return;
  }

  String type = doc["type"] | "UNKNOWN";
  int beepTimes = doc["beepTimes"] | 3;

  Serial.println(" CẢNH BÁO: " + type);

  // Nháy đèn đỏ 3 lần
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_RED, HIGH); delay(200);
    digitalWrite(LED_RED, LOW);  delay(100);
  }

  beep(beepTimes);
  setLight(lightState);  // khôi phục trạng thái
}

//KẾT NỐI WIFI
void setupWiFi() {
  Serial.print("Đang kết nối WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n WiFi OK! IP: " + WiFi.localIP().toString());
}

//KẾT NỐI MQTT
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print(" Đang kết nối MQTT...");
    if (mqttClient.connect(MQTT_CLIENT_ID)) {
      Serial.println(" OK!");
      mqttClient.subscribe(TOPIC_ALERT);
      Serial.println(" Subscribe: " + String(TOPIC_ALERT));
    } else {
      Serial.print(" Thất bại, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" → thử lại sau 2s");
      delay(2000);
    }
  }
}

//SETUP
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  // Test LED lúc khởi động
  digitalWrite(LED_RED, HIGH);
  digitalWrite(LED_YELLOW, HIGH);
  digitalWrite(LED_GREEN, HIGH);
  delay(600);
  digitalWrite(LED_RED, LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_GREEN, LOW);

  Serial.println(" ESP32 Traffic Light khởi động...");

  setupWiFi();

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  setLight(lightState);  // bắt đầu XANH
  Serial.println(" Sẵn sàng!");
}

//LOOP
void loop() {
  if (!mqttClient.connected()) reconnectMQTT();
  mqttClient.loop();

  // Đếm giờ đèn mỗi 1 giây
  if (millis() - lastTick >= 1000) {
    lastTick = millis();
    countdown--;

    // Publish trạng thái đèn lên MQTT mỗi giây
    StaticJsonDocument<128> doc;
    doc["status"] = lightName(lightState);
    doc["remainingSeconds"] = countdown;
    char buf[128];
    serializeJson(doc, buf);
    mqttClient.publish(TOPIC_LIGHT, buf);

    // Chuyển đèn khi hết giờ
    if (countdown <= 0) {
      lightState = (lightState + 1) % 3;
      if (lightState == 0)      countdown = TIME_RED;
      else if (lightState == 1) countdown = TIME_YELLOW;
      else                      countdown = TIME_GREEN;
      setLight(lightState);
      Serial.println(" Đèn: " + String(lightName(lightState)) + " (" + countdown + "s)");
    }
  }
}