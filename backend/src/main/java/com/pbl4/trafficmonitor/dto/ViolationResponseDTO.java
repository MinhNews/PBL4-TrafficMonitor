package com.pbl4.trafficmonitor.dto;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ViolationResponseDTO {
    private Long id;
    private String type;              // "NO_HELMET" hoặc "RED_LIGHT_CROSS"
    private String typeDisplay;       // "Không đội mũ bảo hiểm" / "Vượt đèn đỏ"
    private String cameraName;        // "Camera 01 - Ngã tư Hòa Khánh"
    private String vehicleType;       // "MOTORCYCLE", "CAR"...
    private Integer confidence;       // 95 (%)
    private String status;            // "PENDING", "CONFIRMED", "DISMISSED"
    private String imageUrl;          // "http://localhost:8080/api/images/uuid.jpg"
    private String detectedAt;        // "2026-09-16T08:30:00"
    private String notes;             // Ghi chú xử lý của CSGT
}
