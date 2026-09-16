package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.dto.CameraResponseDTO;
import com.pbl4.trafficmonitor.service.CameraService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/cameras")
@RequiredArgsConstructor
public class CameraController {
    private final CameraService cameraService;

    @GetMapping
    public ResponseEntity<List<CameraResponseDTO>> getCameras() {
        return ResponseEntity.ok(cameraService.getAllActiveCameras());
    }
}
