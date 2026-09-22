package com.pbl4.trafficmonitor.util;

import com.pbl4.trafficmonitor.enums.VehicleType;
import com.pbl4.trafficmonitor.enums.ViolationType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

public class PenaltyRuleHelper {

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PenaltyInfo {
        private String fineAmount; // Ví dụ: "18.000.000 - 20.000.000 VNĐ"
        private Integer penaltyPoints; // Số điểm trừ GPLX (ví dụ: 4)
        private String legalBasis; // Căn cứ điều khoản Nghị định 168/2024
    }

    /**
     * Tra cứu mức phạt và trừ điểm chuẩn Nghị định 168/2024/NĐ-CP
     */
    public static PenaltyInfo calculatePenalty(ViolationType violationType, VehicleType vehicleType) {
        if (violationType == null) {
            return PenaltyInfo.builder()
                    .fineAmount("Đang cập nhật")
                    .penaltyPoints(0)
                    .legalBasis("Luật TTATGTĐB 2024")
                    .build();
        }

        // 1. Lỗi Không đội mũ bảo hiểm (chủ yếu xe máy)
        if (violationType == ViolationType.NO_HELMET) {
            return PenaltyInfo.builder()
                    .fineAmount("800.000 - 1.000.000 VNĐ")
                    .penaltyPoints(0)
                    .legalBasis("Điểm b Khoản 4 Điều 7 Nghị định 168/2024/NĐ-CP")
                    .build();
        }

        // 2. Lỗi Vượt đèn đỏ
        if (violationType == ViolationType.RED_LIGHT_CROSS) {
            if (vehicleType == VehicleType.CAR || vehicleType == VehicleType.TRUCK || vehicleType == VehicleType.BUS) {
                // Ô tô, xe tải, xe khách vượt đèn đỏ
                return PenaltyInfo.builder()
                        .fineAmount("18.000.000 - 20.000.000 VNĐ")
                        .penaltyPoints(4)
                        .legalBasis("Điểm a Khoản 9 Điều 6 Nghị định 168/2024/NĐ-CP")
                        .build();
            } else {
                // Xe máy, xe mô tô vượt đèn đỏ
                return PenaltyInfo.builder()
                        .fineAmount("4.000.000 - 6.000.000 VNĐ")
                        .penaltyPoints(4)
                        .legalBasis("Điểm c Khoản 7 Điều 7 Nghị định 168/2024/NĐ-CP")
                        .build();
            }
        }

        return PenaltyInfo.builder()
                .fineAmount("Theo quy định hiện hành")
                .penaltyPoints(0)
                .legalBasis("Nghị định 168/2024/NĐ-CP")
                .build();
    }
}
