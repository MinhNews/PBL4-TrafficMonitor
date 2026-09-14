package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.Violation;
import com.pbl4.trafficmonitor.enums.ViolationType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;

@Repository
public interface ViolationRepository extends JpaRepository<Violation, Long> {
    
    // Lấy 10 vi phạm mới nhất để hiển thị real-time trên Web
    List<Violation> findTop10ByOrderByDetectedAtDesc();

    // Thẻ StatCard 1: Tổng số vi phạm trong ngày hôm nay
    @Query("SELECT COUNT(v) FROM Violation v WHERE DATE(v.detectedAt) = CURRENT_DATE")
    Long countTodayViolations();

    // Thẻ StatCard 2 & 3: Tổng số theo từng loại lỗi (Không mũ hoặc Vượt đèn đỏ)
    @Query("SELECT COUNT(v) FROM Violation v WHERE v.violationType = :type AND DATE(v.detectedAt) = CURRENT_DATE")
    Long countTodayByType(ViolationType type);

    // Biểu đồ cột: Thống kê số vi phạm theo từng khung giờ trong ngày (0h -> 23h)
    @Query("SELECT HOUR(v.detectedAt) as hour, COUNT(v) as count FROM Violation v WHERE DATE(v.detectedAt) = :date GROUP BY HOUR(v.detectedAt)")
    List<Object[]> countByHourOnDate(LocalDate date);
}
