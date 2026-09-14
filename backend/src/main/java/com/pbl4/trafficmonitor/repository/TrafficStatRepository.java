package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.TrafficStat;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface TrafficStatRepository extends JpaRepository<TrafficStat, Long> {
    // Tìm bản ghi thống kê của 1 camera vào 1 giờ cụ thể
    Optional<TrafficStat> findByCameraIdAndStatDateAndStatHour(Long cameraId, LocalDate date, Integer hour);
    
    // Lấy thống kê 24 giờ của 1 camera
    List<TrafficStat> findByCameraIdAndStatDateOrderByStatHour(Long cameraId, LocalDate date);

    // Thẻ StatCard 4: Tổng số lượt xe đã lưu thông qua ngã tư hôm nay
    @Query("SELECT COALESCE(SUM(t.vehicleCount), 0) FROM TrafficStat t WHERE t.statDate = CURRENT_DATE")
    Long sumTodayVehicles();
}
