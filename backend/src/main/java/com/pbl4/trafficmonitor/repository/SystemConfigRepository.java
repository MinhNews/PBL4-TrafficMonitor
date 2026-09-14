package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.SystemConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface SystemConfigRepository extends JpaRepository<SystemConfig, Long> {
    // Tìm cấu hình theo tên key (VD: "ai.confidence.threshold")
    Optional<SystemConfig> findByConfigKey(String key);
}
