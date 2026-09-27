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
        LocalDate d = (date != null && !date.trim().isEmpty()) ? LocalDate.parse(date.trim()) : LocalDate.now();
        return ResponseEntity.ok(statsService.getHourlyStats(d));
    }

    @PostMapping("/flow")
    public ResponseEntity<?> recordTrafficFlow(@RequestBody java.util.Map<String, Object> body) {
        Long cameraId = body.get("cameraId") != null ? Long.valueOf(body.get("cameraId").toString()) : 1L;
        Integer count = body.get("count") != null ? Integer.valueOf(body.get("count").toString()) : 1;
        String vehicleType = body.get("vehicleType") != null ? body.get("vehicleType").toString() : "vehicle";
        statsService.recordVehicleCount(cameraId, count, vehicleType);
        return ResponseEntity.ok(java.util.Map.of("success", true, "recorded", count, "vehicleType", vehicleType));
    }
}
