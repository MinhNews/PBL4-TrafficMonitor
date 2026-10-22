package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.service.ViolationPdfService;
import com.pbl4.trafficmonitor.service.ViolationService;
import com.pbl4.trafficmonitor.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/violations")
@RequiredArgsConstructor
public class ViolationController {

    private final ViolationService violationService;
    private final ViolationPdfService violationPdfService;
    private final JwtUtil jwtUtil;

    /**
     * Đọc username từ header Authorization nếu có.
     * Trả null khi không có token / token không hợp lệ (hệ thống chưa chặn request,
     * nên chỉ dùng để ghi nhận ai đã duyệt).
     */
    private String resolveUsername(String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return null;
        }
        try {
            String token = authHeader.substring(7);
            return jwtUtil.validateToken(token) ? jwtUtil.getUsername(token) : null;
        } catch (Exception e) {
            return null;
        }
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> createViolation(@RequestBody ViolationCreateDTO dto) {
        ViolationResponseDTO res = violationService.createViolation(dto);
        return ResponseEntity.ok(Map.of("id", res.getId(), "status", "SAVED"));
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> getViolations(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(violationService.getViolations(page, size, type, status));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ViolationResponseDTO> getById(@PathVariable Long id) {
        return ResponseEntity.ok(violationService.getById(id));
    }

    /**
     * C3: Xuất biên bản xử phạt dạng PDF (có ảnh bằng chứng + mức phạt + căn cứ pháp lý).
     * Dùng "inline" để trình duyệt mở xem trước, người dùng vẫn tải về được.
     */
    @GetMapping("/{id}/pdf")
    public ResponseEntity<byte[]> exportPdf(@PathVariable Long id) {
        byte[] pdf = violationPdfService.buildPdf(id);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "inline; filename=\"bien-ban-vi-pham-" + id + ".pdf\"")
                .contentType(MediaType.APPLICATION_PDF)
                .contentLength(pdf.length)
                .body(pdf);
    }

    @PatchMapping("/{id}/confirm")
    public ResponseEntity<ViolationResponseDTO> confirm(@PathVariable Long id,
            @RequestBody(required = false) Map<String, String> body,
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        String notes = body != null ? body.get("notes") : null;
        return ResponseEntity.ok(violationService.confirmViolation(id, notes, resolveUsername(authHeader)));
    }

    @PatchMapping("/{id}/dismiss")
    public ResponseEntity<ViolationResponseDTO> dismiss(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        String notes = body != null ? body.get("notes") : null;
        return ResponseEntity.ok(violationService.dismissViolation(id, notes));
    }

    @PostMapping("/test-alert")
    public ResponseEntity<Map<String, Object>> testAlert() {
        violationService.triggerTestAlert();
        return ResponseEntity.ok(Map.of(
            "status", "SUCCESS",
            "message", "Đã gửi lệnh kích hoạt còi hú tới ESP32 qua kênh MQTT Mosquitto thành công!"
        ));
    }
}
