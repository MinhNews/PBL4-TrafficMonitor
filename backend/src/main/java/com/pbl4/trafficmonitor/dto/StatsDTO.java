package com.pbl4.trafficmonitor.dto;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StatsDTO {
    private Long totalViolations;      // Tổng số vi phạm hôm nay
    private Long noHelmetCount;        // Số vụ không đội mũ
    private Long redLightCount;        // Số vụ vượt đèn đỏ
    private Long vehiclesPassedToday;  // Tổng lượt xe chạy qua ngã tư
}
