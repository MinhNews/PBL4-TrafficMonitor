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

    public StatsDTO getTodayStats() {
        return StatsDTO.builder()
            .totalViolations(violationRepo.countTodayViolations())
            .noHelmetCount(violationRepo.countTodayByType(ViolationType.NO_HELMET))
            .redLightCount(violationRepo.countTodayByType(ViolationType.RED_LIGHT_CROSS))
            .vehiclesPassedToday(trafficStatRepo.sumTodayVehicles())
            .build();
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
