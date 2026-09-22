package com.pbl4.trafficmonitor.service;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.entity.*;
import com.pbl4.trafficmonitor.enums.*;
import com.pbl4.trafficmonitor.repository.*;
import com.pbl4.trafficmonitor.util.PenaltyRuleHelper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.*;
import org.springframework.messaging.simp.SimpMessagingTemplate;
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
    private final ImageStorageService imageStorageService; // Lưu local làm fallback dự phòng
    private final CloudinaryStorageService cloudinaryStorageService; // Upload ảnh Cloud
    private final SimpMessagingTemplate messagingTemplate; // Đẩy thời gian thực WebSocket
    private final MqttPublisherService mqttPublisherService; // Bắn lệnh còi hú sang ESP32

    @Transactional
    public ViolationResponseDTO createViolation(ViolationCreateDTO dto) {
        log.info("🚨 [AI PHÁT HIỆN VI PHẠM] Camera: {}, Loại: {}, Xe: {}, Độ tin cậy: {}",
                dto.getCameraId(), dto.getViolationType(), dto.getVehicleType(), dto.getConfidence());

        Camera camera = cameraRepo.findById(dto.getCameraId())
                .orElseThrow(() -> new RuntimeException("Không tìm thấy camera ID: " + dto.getCameraId()));

        // BƯỚC 1: Upload ảnh bằng chứng lên Cloudinary lấy link HTTPS vĩnh viễn
        String imageUrl = null;
        String fileName = null;
        if (dto.getImageBase64() != null && !dto.getImageBase64().trim().isEmpty()) {
            imageUrl = cloudinaryStorageService.uploadBase64Image(dto.getImageBase64());

            // Cơ chế Fallback an toàn: Nếu mạng Cloudinary lỗi, tự lưu ảnh vào ổ cứng cục
            // bộ
            if (imageUrl == null) {
                try {
                    fileName = imageStorageService.saveBase64Image(dto.getImageBase64());
                    imageUrl = "http://localhost:8080/api/images/" + fileName;
                } catch (Exception e) {
                    log.error("⚠️ Lỗi fallback lưu ảnh local: {}", e.getMessage());
                }
            }
        }

        // BƯỚC 2: Parse kiểu dữ liệu Enum
        ViolationType vType = ViolationType.valueOf(dto.getViolationType());
        VehicleType vehType = dto.getVehicleType() != null ? VehicleType.valueOf(dto.getVehicleType())
                : VehicleType.UNKNOWN;

        // BƯỚC 3: Lưu bản ghi vi phạm vào CSDL MySQL
        Violation violation = Violation.builder()
                .camera(camera)
                .violationType(vType)
                .vehicleType(vehType)
                .confidence(dto.getConfidence())
                .status(ViolationStatus.PENDING)
                .evidenceImagePath(fileName)
                .evidenceImageUrl(imageUrl)
                .build();

        violation = violationRepo.save(violation);
        log.info("💾 Đã lưu vi phạm #{} vào MySQL thành công!", violation.getId());

        // Chuyển đổi sang Response DTO (đã được tự động áp mức phạt Nghị định 168)
        ViolationResponseDTO responseDTO = toResponseDTO(violation);

        // BƯỚC 4: Bắn WebSocket STOMP xuống React Dashboard (tự động nảy số, không cần
        // F5)
        try {
            messagingTemplate.convertAndSend("/topic/violations", responseDTO);
            log.info("📡 [WEBSOCKET] Đã đẩy vi phạm #{} xuống kênh /topic/violations", violation.getId());
        } catch (Exception e) {
            log.error("❌ Lỗi đẩy WebSocket: {}", e.getMessage());
        }

        // BƯỚC 5: Bắn MQTT sang bo ESP32 thật của Khoa (Kích hoạt còi hú hiện trường)
        try {
            String alertPayload = String.format(
                    "{\"type\":\"%s\",\"vehicleType\":\"%s\",\"fine\":\"%s\",\"beepTimes\":4,\"violationId\":%d}",
                    vType.name(), vehType.name(), responseDTO.getFineAmount(), violation.getId());
            mqttPublisherService.publishAlert(alertPayload);
            log.info("🔊 [MQTT ESP32] Đã gửi lệnh hú còi tới bo mạch thật: {}", alertPayload);
        } catch (Exception e) {
            log.error("❌ Lỗi bắn MQTT sang ESP32: {}", e.getMessage());
        }

        return responseDTO;
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
        // Tự động tra cứu mức phạt và điểm trừ theo Nghị định 168/2024/NĐ-CP
        PenaltyRuleHelper.PenaltyInfo penalty = PenaltyRuleHelper.calculatePenalty(
                v.getViolationType(), v.getVehicleType());

        return ViolationResponseDTO.builder()
                .id(v.getId())
                .type(v.getViolationType().name())
                .typeDisplay(v.getViolationType() == ViolationType.NO_HELMET ? "Không đội mũ bảo hiểm" : "Vượt đèn đỏ")
                .cameraName(v.getCamera() != null ? v.getCamera().getName() : "Camera ngã tư")
                .vehicleType(v.getVehicleType() != null ? v.getVehicleType().name() : "UNKNOWN")
                .confidence(v.getConfidence() != null ? (int) (v.getConfidence() * 100) : 0)
                .status(v.getStatus() != null ? v.getStatus().name() : "PENDING")
                .imageUrl(v.getEvidenceImageUrl())
                .detectedAt(v.getDetectedAt() != null ? v.getDetectedAt().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
                        : null)
                .notes(v.getNotes())
                // 3 thông tin pháp lý từ Nghị định 168/2024
                .fineAmount(penalty.getFineAmount())
                .penaltyPoints(penalty.getPenaltyPoints())
                .legalBasis(penalty.getLegalBasis())
                .build();
    }
}
