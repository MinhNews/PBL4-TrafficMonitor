package com.pbl4.trafficmonitor.service;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.enums.ViolationType;
import com.pbl4.trafficmonitor.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.time.LocalDate;
import java.util.*;

@Service
@RequiredArgsConstructor
public class StatsService {

    private final ViolationRepository violationRepo;
    private final TrafficStatRepository trafficStatRepo;
    private final CameraRepository cameraRepo;

    public StatsDTO getTodayStats() {
        Long todayViolations = violationRepo.countTodayViolations();
        // Lấy đúng số liệu thật từ bảng traffic_stats (AI đếm qua /api/stats/flow).
        // Không sinh số ước lượng: nếu chưa có dữ liệu thì trả 0.
        Long vehiclesPassed = trafficStatRepo.sumTodayVehicles();
        if (vehiclesPassed == null) {
            vehiclesPassed = 0L;
        }

        return StatsDTO.builder()
            .totalViolations(todayViolations != null ? todayViolations : 0L)
            .noHelmetCount(violationRepo.countTodayByType(ViolationType.NO_HELMET))
            .redLightCount(violationRepo.countTodayByType(ViolationType.RED_LIGHT_CROSS))
            .vehiclesPassedToday(vehiclesPassed)
            .build();
    }

    @org.springframework.transaction.annotation.Transactional
    public void recordVehicleCount(Long cameraId, int count, String vehicleType) {
        LocalDate today = LocalDate.now();
        int currentHour = java.time.LocalTime.now().getHour();

        com.pbl4.trafficmonitor.entity.Camera camera = cameraRepo.findById(cameraId).orElse(null);
        if (camera == null) {
            return;
        }

        com.pbl4.trafficmonitor.entity.TrafficStat stat = trafficStatRepo
                .findByCameraIdAndStatDateAndStatHour(cameraId, today, currentHour)
                .orElseGet(() -> com.pbl4.trafficmonitor.entity.TrafficStat.builder()
                        .camera(camera)
                        .statDate(today)
                        .statHour(currentHour)
                        .vehicleCount(0)
                        .motorcycleCount(0)
                        .carCount(0)
                        .violationCount(0)
                        .noHelmetCount(0)
                        .redLightCount(0)
                        .build());

        int currentTotal = stat.getVehicleCount() != null ? stat.getVehicleCount() : 0;
        stat.setVehicleCount(currentTotal + count);

        if ("motorcycle".equalsIgnoreCase(vehicleType)) {
            stat.setMotorcycleCount((stat.getMotorcycleCount() != null ? stat.getMotorcycleCount() : 0) + count);
        } else if ("car".equalsIgnoreCase(vehicleType) || "truck".equalsIgnoreCase(vehicleType) || "bus".equalsIgnoreCase(vehicleType)) {
            stat.setCarCount((stat.getCarCount() != null ? stat.getCarCount() : 0) + count);
        }

        trafficStatRepo.save(stat);
    }

    public List<HourlyStatDTO> getHourlyStats(LocalDate date) {
        // 1. Số vi phạm theo giờ (bảng violations)
        List<Object[]> raw = violationRepo.countByHourOnDate(date);
        Map<Integer, Long> hourMap = new HashMap<>();
        for (Object[] row : raw) {
            hourMap.put(((Number) row[0]).intValue(), ((Number) row[1]).longValue());
        }

        // 2. C1: Lưu lượng xe theo giờ (bảng traffic_stats đã có sẵn dữ liệu)
        Map<Integer, long[]> flowMap = new HashMap<>();
        for (Object[] row : trafficStatRepo.sumVehicleStatsByHourOnDate(date)) {
            int h = ((Number) row[0]).intValue();
            flowMap.put(h, new long[]{
                    toLong(row[1]),  // vehicleCount
                    toLong(row[2]),  // motorcycleCount
                    toLong(row[3])   // carCount
            });
        }

        List<HourlyStatDTO> result = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            long[] flow = flowMap.getOrDefault(h, new long[]{0L, 0L, 0L});
            result.add(HourlyStatDTO.builder()
                .hour(h)
                .count(hourMap.getOrDefault(h, 0L))
                .label(String.format("%02d:00", h))
                .vehicleCount(flow[0])
                .motorcycleCount(flow[1])
                .carCount(flow[2])
                .build());
        }
        return result;
    }

    /** C1: SUM() có thể trả null (cột chưa có dữ liệu) hoặc BigDecimal -> ép an toàn về long. */
    private static long toLong(Object value) {
        return value == null ? 0L : ((Number) value).longValue();
    }
}
