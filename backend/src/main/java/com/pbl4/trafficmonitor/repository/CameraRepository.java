package com.pbl4.trafficmonitor.repository;

import com.pbl4.trafficmonitor.entity.Camera;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface CameraRepository extends JpaRepository<Camera, Long> {
    // Lấy danh sách camera đang bật
    List<Camera> findByIsActiveTrue();

    // Lấy các camera thuộc về 1 ngã tư
    List<Camera> findByRegionId(Long regionId);

    // Tìm camera theo URL luồng video
    Optional<Camera> findByStreamUrl(String streamUrl);
}
