package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity 
@Table(name = "alerts")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class Alert {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Cảnh báo này phát ra từ vụ vi phạm nào?
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "violation_id", nullable = false)
    private Violation violation;

    @Column(name = "alert_type", length = 30)
    private String alertType;           // BUZZER, LED_FLASH

    @Column(name = "mqtt_topic", length = 100)
    private String mqttTopic;          // "traffic/alert"

    @Column(name = "mqtt_payload", columnDefinition = "TEXT")
    private String mqttPayload;        // Nội dung JSON gửi đi

    @Column(name = "is_sent")
    @Builder.Default
    private Boolean isSent = false;

    @Column(name = "sent_at")
    private LocalDateTime sentAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() { 
        this.createdAt = LocalDateTime.now(); 
    }
}
