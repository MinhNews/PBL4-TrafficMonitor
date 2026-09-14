package com.pbl4.trafficmonitor.entity;

import com.pbl4.trafficmonitor.enums.*;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity 
@Table(name = "violations")
@Data 
@Builder 
@NoArgsConstructor 
@AllArgsConstructor
public class Violation {
    @Id 
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Vi phạm xảy ra tại Camera nào?
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "camera_id", nullable = false)
    private Camera camera;

    // Loại lỗi: NO_HELMET hoặc RED_LIGHT_CROSS
    @Enumerated(EnumType.STRING)
    @Column(name = "violation_type", nullable = false, length = 30)
    private ViolationType violationType;

    // Loại phương tiện: MOTORCYCLE, CAR,...
    @Enumerated(EnumType.STRING)
    @Column(name = "vehicle_type", length = 30)
    private VehicleType vehicleType;

    @Column(precision = 5, scale = 4)
    private Double confidence;   // Độ tin cậy AI (VD: 0.9520)

    // Trạng thái: PENDING (chờ duyệt), CONFIRMED (đã phạt), DISMISSED (bác bỏ)
    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    @Builder.Default
    private ViolationStatus status = ViolationStatus.PENDING;

    @Column(name = "evidence_image_path", length = 500)
    private String evidenceImagePath;    // Đường dẫn file ảnh lưu trên ổ cứng

    @Column(name = "evidence_image_url", length = 500)
    private String evidenceImageUrl;     // Đường dẫn URL để React load ảnh xem

    @Column(columnDefinition = "TEXT")
    private String notes;                // Ghi chú của cán bộ CSGT khi duyệt

    @Column(name = "detected_at")
    private LocalDateTime detectedAt;    // Thời điểm vi phạm

    // Cán bộ CSGT nào đã bấm duyệt hồ sơ này?
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "confirmed_by")
    private User confirmedBy;

    @Column(name = "confirmed_at")
    private LocalDateTime confirmedAt;

    @PrePersist
    protected void onCreate() {
        this.detectedAt = LocalDateTime.now();
        if (this.status == null) {
            this.status = ViolationStatus.PENDING;
        }
    }
}
