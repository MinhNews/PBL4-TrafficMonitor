package com.pbl4.trafficmonitor.service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class MqttPublisherService {

    @Value("${mqtt.broker-url:tcp://test.mosquitto.org:1883}")
    private String brokerUrl;

    @Value("${mqtt.client-id:pbl4-spring-backend}")
    private String clientId;

    @Value("${mqtt.alert-topic:pbl4/nhom3/traffic/alert}")
    private String alertTopic;

    private MqttClient mqttClient;

    @PostConstruct
    public void init() {
        try {
            log.info("🔌 Đang kết nối tới MQTT Broker: {}", brokerUrl);
            mqttClient = new MqttClient(brokerUrl, clientId + "-" + System.currentTimeMillis(),
                    new MemoryPersistence());

            MqttConnectOptions options = new MqttConnectOptions();
            options.setAutomaticReconnect(true); // Tự kết nối lại nếu rớt mạng
            options.setCleanSession(true);
            options.setConnectionTimeout(10); // Timeout 10s
            options.setKeepAliveInterval(60);

            mqttClient.connect(options);
            log.info("✅ Kết nối MQTT Broker thành công! Sẵn sàng bắn tín hiệu cảnh báo.");
        } catch (MqttException e) {
            log.error("⚠️ Không thể kết nối MQTT Broker lúc khởi động: {}. Sẽ tự kết nối lại khi có mạng.",
                    e.getMessage());
        }
    }

    /**
     * Bắn tín hiệu cảnh báo vi phạm ra bo ESP32 thật
     * 
     * @param payload Chuỗi JSON chứa loại vi phạm và lệnh hú còi
     */
    public void publishAlert(String payload) {
        publish(alertTopic, payload);
    }

    /**
     * Hàm publish tổng quát tới một topic bất kỳ
     */
    public void publish(String topic, String payload) {
        try {
            if (mqttClient == null || !mqttClient.isConnected()) {
                log.warn("⚠️ MQTT Client chưa kết nối. Đang thử kết nối lại...");
                if (mqttClient != null) {
                    mqttClient.reconnect();
                }
            }

            MqttMessage message = new MqttMessage(payload.getBytes());
            message.setQos(1); // QoS 1: Đảm bảo thông điệp gửi tới Broker ít nhất 1 lần

            mqttClient.publish(topic, message);
            log.info("📢 [MQTT SENT] Đã gửi lệnh tới kênh [{}]: {}", topic, payload);
        } catch (Exception e) {
            log.error("❌ Lỗi khi gửi MQTT tới kênh [{}]: {}", topic, e.getMessage());
        }
    }

    @PreDestroy
    public void cleanup() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
                mqttClient.close();
                log.info("🔌 Đã ngắt kết nối MQTT an toàn.");
            }
        } catch (MqttException e) {
            log.error("Lỗi khi ngắt kết nối MQTT: {}", e.getMessage());
        }
    }
}
