package com.pbl4.trafficmonitor.dto;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CameraResponseDTO {
    private Long id;
    private String name;               // Tên camera
    private String regionName;         // Tên khu vực / ngã tư
    private String locationDescription;// Mô tả vị trí
    private String streamUrl;          // Link luồng RTSP / MJPEG
    private Boolean isActive;          // Camera có đang hoạt động không
}
