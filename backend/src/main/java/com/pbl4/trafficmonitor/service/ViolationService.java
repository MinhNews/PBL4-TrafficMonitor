package com.pbl4.trafficmonitor.service;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.entity.*;
import com.pbl4.trafficmonitor.enums.*;
import com.pbl4.trafficmonitor.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class ViolationService {

    private final ViolationRepository violationRepo;
    private final CameraRepository cameraRepo;
    private final ImageStorageService imageStorageService;

    @Transactional
    public ViolationResponseDTO createViolation(ViolationCreateDTO dto) {
        log.info("Nhận vi phạm mới: camera={}, type={}, conf={}", 
                 dto.getCameraId(), dto.getViolationType(), dto.getConfidence());

        Camera camera = cameraRepo.findById(dto.getCameraId())
            .orElseThrow(() -> new RuntimeException("Không tìm thấy camera ID: " + dto.getCameraId()));

        String fileName = null;
        String imageUrl = null;
        try {
            if (dto.getImageBase64() != null && !dto.getImageBase64().isEmpty()) {
                fileName = imageStorageService.saveBase64Image(dto.getImageBase64());
                imageUrl = "http://localhost:8080/api/images/" + fileName;
            }
        } catch (Exception e) {
            log.error("Lỗi lưu ảnh: {}", e.getMessage());
        }

        Violation violation = Violation.builder()
            .camera(camera)
            .violationType(ViolationType.valueOf(dto.getViolationType()))
            .vehicleType(dto.getVehicleType() != null ? VehicleType.valueOf(dto.getVehicleType()) : VehicleType.UNKNOWN)
            .confidence(dto.getConfidence())
            .status(ViolationStatus.PENDING)
            .evidenceImagePath(fileName)
            .evidenceImageUrl(imageUrl)
            .build();

        violation = violationRepo.save(violation);
        return toResponseDTO(violation);
    }

    public Map<String, Object> getViolations(int page, int size, String type, String status) {
        Pageable pageable = PageRequest.of(page, size, Sort.by("detectedAt").descending());
        Page<Violation> pageResult = violationRepo.findAll(pageable);

        List<ViolationResponseDTO> dtos = pageResult.getContent().stream()
            .map(this::toResponseDTO).toList();

        Map<String, Object> response = new HashMap<>();
        response.put("content", dtos);
        response.put("currentPage", page);
        response.put("totalElements", pageResult.getTotalElements());
        response.put("totalPages", pageResult.getTotalPages());
        return response;
    }

    public ViolationResponseDTO getById(Long id) {
        Violation v = violationRepo.findById(id)
            .orElseThrow(() -> new RuntimeException("Không tìm thấy vi phạm ID: " + id));
        return toResponseDTO(v);
    }

    @Transactional
    public ViolationResponseDTO confirmViolation(Long id, String notes) {
        Violation v = violationRepo.findById(id)
            .orElseThrow(() -> new RuntimeException("Không tìm thấy vi phạm ID: " + id));
        v.setStatus(ViolationStatus.CONFIRMED);
        v.setNotes(notes);
        v.setConfirmedAt(java.time.LocalDateTime.now());
        return toResponseDTO(violationRepo.save(v));
    }

    @Transactional
    public ViolationResponseDTO dismissViolation(Long id, String notes) {
        Violation v = violationRepo.findById(id)
            .orElseThrow(() -> new RuntimeException("Không tìm thấy vi phạm ID: " + id));
        v.setStatus(ViolationStatus.DISMISSED);
        v.setNotes(notes);
        return toResponseDTO(violationRepo.save(v));
    }

    public ViolationResponseDTO toResponseDTO(Violation v) {
        return ViolationResponseDTO.builder()
            .id(v.getId())
            .type(v.getViolationType().name())
            .typeDisplay(v.getViolationType() == ViolationType.NO_HELMET ? "Không đội mũ bảo hiểm" : "Vượt đèn đỏ")
            .cameraName(v.getCamera() != null ? v.getCamera().getName() : "Camera ngã tư")
            .vehicleType(v.getVehicleType() != null ? v.getVehicleType().name() : "UNKNOWN")
            .confidence(v.getConfidence() != null ? (int)(v.getConfidence() * 100) : 0)
            .status(v.getStatus() != null ? v.getStatus().name() : "PENDING")
            .imageUrl(v.getEvidenceImageUrl())
            .detectedAt(v.getDetectedAt() != null ? v.getDetectedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME) : null)
            .notes(v.getNotes())
            .build();
    }
}
