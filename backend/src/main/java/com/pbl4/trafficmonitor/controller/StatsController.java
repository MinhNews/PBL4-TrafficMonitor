package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.service.StatsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {
    private final StatsService statsService;

    @GetMapping("/today")
    public ResponseEntity<StatsDTO> getTodayStats() {
        return ResponseEntity.ok(statsService.getTodayStats());
    }

    @GetMapping("/hourly")
    public ResponseEntity<List<HourlyStatDTO>> getHourlyStats(@RequestParam(required = false) String date) {
        LocalDate d = (date != null) ? LocalDate.parse(date) : LocalDate.now();
        return ResponseEntity.ok(statsService.getHourlyStats(d));
    }
}
