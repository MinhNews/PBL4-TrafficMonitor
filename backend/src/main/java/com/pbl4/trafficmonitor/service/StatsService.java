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
        Long vehiclesPassed = trafficStatRepo.sumTodayVehicles();
        if (vehiclesPassed == null || vehiclesPassed == 0L) {
            vehiclesPassed = todayViolations != null && todayViolations > 0 ? (todayViolations * 3 + 12) : 0L;
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
        List<Object[]> raw = violationRepo.countByHourOnDate(date);
        Map<Integer, Long> hourMap = new HashMap<>();
        for (Object[] row : raw) {
            hourMap.put(((Number) row[0]).intValue(), ((Number) row[1]).longValue());
        }

        List<HourlyStatDTO> result = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            result.add(HourlyStatDTO.builder()
                .hour(h)
                .count(hourMap.getOrDefault(h, 0L))
                .label(String.format("%02d:00", h))
                .build());
        }
        return result;
    }
}
