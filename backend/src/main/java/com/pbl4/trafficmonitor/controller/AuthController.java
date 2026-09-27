package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.service.AuthService;
import com.pbl4.trafficmonitor.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {

    private final AuthService authService;
    private final JwtUtil jwtUtil;

    /**
     * POST /api/auth/login
     * Body: { "username": "admin", "password": "admin@2026" }
     * Response: { "token": "...", "role": "ADMIN", "fullName": "...", ... }
     */
    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> body) {
        try {
            String username = body.get("username");
            String password = body.get("password");

            if (username == null || password == null || username.isBlank() || password.isBlank()) {
                return ResponseEntity.badRequest().body(Map.of("error", "Vui lòng nhập đủ tên đăng nhập và mật khẩu."));
            }

            Map<String, Object> result = authService.login(username.trim(), password);
            return ResponseEntity.ok(result);

        } catch (RuntimeException e) {
            log.warn("❌ [AUTH] Đăng nhập thất bại: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * GET /api/auth/me
     * Header: Authorization: Bearer <token>
     * Response: Thông tin người dùng hiện tại
     */
    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> getCurrentUser(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        try {
            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body(Map.of("error", "Phiên làm việc không hợp lệ. Vui lòng đăng nhập lại."));
            }
            String token = authHeader.substring(7);
            Map<String, Object> user = authService.getCurrentUser(token);
            return ResponseEntity.ok(user);
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * POST /api/auth/logout  (stateless - client clears token)
     */
    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout() {
        return ResponseEntity.ok(Map.of("message", "Đã đăng xuất khỏi hệ thống an toàn."));
    }

    /**
     * POST /api/auth/validate  - Kiểm tra token còn hiệu lực
     */
    @PostMapping("/validate")
    public ResponseEntity<Map<String, Object>> validate(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            if (jwtUtil.validateToken(token)) {
                return ResponseEntity.ok(Map.of("valid", true, "role", jwtUtil.getRole(token)));
            }
        }
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("valid", false));
    }
}
