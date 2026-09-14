package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity 
@Table(name = "traffic_stats")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class TrafficStat {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "camera_id", nullable = false)
    private Camera camera;

    @Column(name = "stat_date", nullable = false)
    private LocalDate statDate;          // Ngày thống kê

    @Column(name = "stat_hour", nullable = false)
    private Integer statHour;            // Khung giờ: 0 đến 23

    @Column(name = "vehicle_count")
    @Builder.Default
    private Integer vehicleCount = 0;    // Tổng số xe đi qua trong giờ này

    @Column(name = "motorcycle_count")
    @Builder.Default
    private Integer motorcycleCount = 0;

    @Column(name = "car_count")
    @Builder.Default
    private Integer carCount = 0;

    @Column(name = "violation_count")
    @Builder.Default
    private Integer violationCount = 0;  // Tổng số vụ vi phạm trong giờ này

    @Column(name = "no_helmet_count")
    @Builder.Default
    private Integer noHelmetCount = 0;

    @Column(name = "red_light_count")
    @Builder.Default
    private Integer redLightCount = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PreUpdate
    protected void onUpdate() { 
        this.updatedAt = LocalDateTime.now(); 
    }
}
