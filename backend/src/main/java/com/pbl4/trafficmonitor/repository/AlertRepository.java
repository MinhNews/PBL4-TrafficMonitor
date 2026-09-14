package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.Alert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface AlertRepository extends JpaRepository<Alert, Long> {
    List<Alert> findByViolationId(Long violationId);
}
