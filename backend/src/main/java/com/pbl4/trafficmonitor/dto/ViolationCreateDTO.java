package com.pbl4.trafficmonitor.dto;

import lombok.Data;

@Data
public class ViolationCreateDTO {
    private Long cameraId;            // ID camera (VD: 1)
    private String violationType;     // "NO_HELMET" hoặc "RED_LIGHT_CROSS"
    private String vehicleType;       // "MOTORCYCLE", "CAR",...
    private Double confidence;        // Độ tin cậy AI (0.00 đến 1.00)
    private String imageBase64;       // Chuỗi ảnh base64 "data:image/jpeg;base64,..."
}
