package com.pbl4.trafficmonitor.dto;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HourlyStatDTO {
    private Integer hour;              // 0 đến 23
    private Long count;                // Số vi phạm trong giờ đó
    private String label;              // Nhãn hiển thị: "08:00", "09:00"...

    // C1: Lưu lượng phương tiện (đọc từ bảng traffic_stats, do AI đẩy qua /api/stats/flow)
    private Long vehicleCount;         // Tổng lượt xe qua ngã tư trong giờ
    private Long motorcycleCount;      // Trong đó: xe máy
    private Long carCount;             // Trong đó: ô tô / tải / khách
}
