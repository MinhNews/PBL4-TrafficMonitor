package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.entity.SystemConfig;
import com.pbl4.trafficmonitor.repository.SystemConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.*;

@RestController
@RequestMapping("/api/config")
@RequiredArgsConstructor
@Slf4j
public class SystemConfigController {

    private final SystemConfigRepository configRepository;

    @GetMapping
    public ResponseEntity<Map<String, String>> getAllConfigs() {
        List<SystemConfig> all = configRepository.findAll();
        Map<String, String> configMap = new HashMap<>();

        // Đảm bảo có các cấu hình mặc định nếu bảng rỗng
        if (all.isEmpty()) {
            saveDefault("STOP_LINE_Y", "468", "Tọa độ vạch dừng ảo trên khung hình AI");
            saveDefault("YOLO_CONF", "0.22", "Ngưỡng tin cậy phát hiện phương tiện của YOLO11");
            saveDefault("CAMERA_LOCATION", "Ngã tư Hòa Khánh, Q. Liên Chiểu, Đà Nẵng", "Vị trí camera giám sát");
            all = configRepository.findAll();
        }

        for (SystemConfig cfg : all) {
            configMap.put(cfg.getConfigKey(), cfg.getConfigValue());
        }

        return ResponseEntity.ok(configMap);
    }

    @PostMapping
    public ResponseEntity<Map<String, String>> updateConfigs(@RequestBody Map<String, Object> updates) {
        log.info("⚙️ Nhận yêu cầu cập nhật cấu hình hệ thống: {}", updates);

        for (Map.Entry<String, Object> entry : updates.entrySet()) {
            String key = entry.getKey();
            String value = String.valueOf(entry.getValue());

            SystemConfig config = configRepository.findByConfigKey(key)
                    .orElse(SystemConfig.builder()
                            .configKey(key)
                            .description("Cấu hình thời gian thực từ Web Dashboard")
                            .build());

            config.setConfigValue(value);
            config.setUpdatedAt(LocalDateTime.now());
            configRepository.save(config);
        }

        log.info("✅ Đã lưu cấu hình vào MySQL database thành công!");
        return getAllConfigs();
    }

    private void saveDefault(String key, String val, String desc) {
        configRepository.save(SystemConfig.builder()
                .configKey(key)
                .configValue(val)
                .description(desc)
                .updatedAt(LocalDateTime.now())
                .build());
    }
}
