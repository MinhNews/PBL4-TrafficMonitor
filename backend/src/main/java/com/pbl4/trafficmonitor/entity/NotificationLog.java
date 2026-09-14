package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity 
@Table(name = "notification_logs")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class NotificationLog {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "violation_id")
    private Long violationId;

    @Column(length = 30)
    private String channel;      // WEBSOCKET, MQTT, EMAIL

    @Column(length = 200)
    private String recipient;

    @Column(columnDefinition = "TEXT")
    private String message;

    @Column(name = "is_delivered")
    @Builder.Default
    private Boolean isDelivered = false;

    @Column(name = "sent_at")
    private LocalDateTime sentAt;

    @PrePersist
    protected void onCreate() { 
        this.sentAt = LocalDateTime.now(); 
    }
}
