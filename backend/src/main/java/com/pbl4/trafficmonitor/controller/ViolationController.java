package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.dto.*;
import com.pbl4.trafficmonitor.service.ViolationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/violations")
@RequiredArgsConstructor
public class ViolationController {

    private final ViolationService violationService;

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

    @PatchMapping("/{id}/confirm")
    public ResponseEntity<ViolationResponseDTO> confirm(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        String notes = body != null ? body.get("notes") : null;
        return ResponseEntity.ok(violationService.confirmViolation(id, notes));
    }

    @PatchMapping("/{id}/dismiss")
    public ResponseEntity<ViolationResponseDTO> dismiss(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        String notes = body != null ? body.get("notes") : null;
        return ResponseEntity.ok(violationService.dismissViolation(id, notes));
    }
}
