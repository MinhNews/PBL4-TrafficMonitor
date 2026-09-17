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
}
