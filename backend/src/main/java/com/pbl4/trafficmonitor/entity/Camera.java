package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity 
@Table(name = "cameras")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class Camera {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Nhiều Camera thuộc về 1 Khu vực / Ngã tư
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "region_id", nullable = false)
    private Region region;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "ip_address", length = 50)
    private String ipAddress;

    @Column(name = "location_description", length = 255)
    private String locationDescription;

    @Column(name = "is_active")
    @Builder.Default
    private Boolean isActive = true;

    @Column(name = "stream_url", length = 500)
    private String streamUrl;    // Đường dẫn lấy luồng video MJPEG từ AI

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() { 
        this.createdAt = LocalDateTime.now(); 
    }
}
