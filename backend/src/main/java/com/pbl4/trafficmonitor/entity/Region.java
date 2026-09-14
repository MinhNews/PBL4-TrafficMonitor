package com.pbl4.trafficmonitor.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity 
@Table(name = "regions")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class Region {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;         // Tên ngã tư (VD: "Ngã tư Hòa Khánh")

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(length = 100)
    @Builder.Default
    private String city = "Đà Nẵng";

    @Column(length = 100)
    private String district;

    @Column(precision = 10, scale = 8)
    private Double latitude;     // Tọa độ vĩ độ (dùng để ghim lên bản đồ)

    @Column(precision = 11, scale = 8)
    private Double longitude;    // Tọa độ kinh độ

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() { 
        this.createdAt = LocalDateTime.now(); 
    }
}
