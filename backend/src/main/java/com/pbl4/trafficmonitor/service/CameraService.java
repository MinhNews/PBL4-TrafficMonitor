package com.pbl4.trafficmonitor.service;

import com.pbl4.trafficmonitor.dto.CameraResponseDTO;
import com.pbl4.trafficmonitor.repository.CameraRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
@RequiredArgsConstructor
public class CameraService {
    private final CameraRepository cameraRepo;

    public List<CameraResponseDTO> getAllActiveCameras() {
        return cameraRepo.findByIsActiveTrue().stream().map(c -> 
            CameraResponseDTO.builder()
                .id(c.getId())
                .name(c.getName())
                .regionName(c.getRegion() != null ? c.getRegion().getName() : "")
                .locationDescription(c.getLocationDescription())
                .streamUrl(c.getStreamUrl())
                .isActive(c.getIsActive())
                .build()
        ).toList();
    }
}
