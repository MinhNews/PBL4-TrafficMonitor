package com.pbl4.trafficmonitor.service;

import com.pbl4.trafficmonitor.entity.User;
import com.pbl4.trafficmonitor.repository.UserRepository;
import com.pbl4.trafficmonitor.util.JwtUtil;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthService {

    private final UserRepository userRepository;
    private final JwtUtil jwtUtil;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder(12);

    /**
     * Khởi tạo tài khoản mặc định nếu DB trống lần đầu.
     * admin / admin@2026 → ADMIN
     * officer / csgt@2026 → OFFICER
     */
    @PostConstruct
    public void seedDefaultUsers() {
        seedUser("admin",   "admin@2026",  "Chỉ Huy Trưởng Trực Ban",   "ADMIN",   "CAND-108920");
        seedUser("officer", "csgt@2026",   "Cán Bộ Giám Sát Giao Thông", "OFFICER", "CAND-204615");
    }

    private void seedUser(String username, String rawPassword, String fullName, String role, String badgeId) {
        var existing = userRepository.findByUsername(username);
        if (existing.isPresent()) {
            User u = existing.get();
            // Kiểm tra xem mật khẩu hiện tại có khớp với rawPassword không, nếu không thì cập nhật lại bằng BCrypt
            if (u.getPassword() == null || !passwordEncoder.matches(rawPassword, u.getPassword())) {
                u.setPassword(passwordEncoder.encode(rawPassword));
                u.setFullName(fullName);
                u.setRole(role);
                u.setEmail(badgeId + "@csgt.vn");
                u.setIsActive(true);
                userRepository.save(u);
                log.info("🔄 [AUTH] Đã cập nhật mật khẩu BCrypt cho tài khoản: {} ({})", username, role);
            }
            return;
        }
        User u = User.builder()
                .username(username)
                .password(passwordEncoder.encode(rawPassword))
                .fullName(fullName)
                .role(role)
                .email(badgeId + "@csgt.vn")
                .isActive(true)
                .build();
        userRepository.save(u);
        log.info("✅ [AUTH] Đã tạo tài khoản mặc định: {} ({})", username, role);
    }

    /**
     * Xác thực đăng nhập và trả về JWT Token nếu hợp lệ.
     */
    public Map<String, Object> login(String username, String password) {
        Optional<User> optUser = userRepository.findByUsername(username);

        if (optUser.isEmpty()) {
            throw new RuntimeException("Tên đăng nhập hoặc mật khẩu không chính xác.");
        }

        User user = optUser.get();

        if (!Boolean.TRUE.equals(user.getIsActive())) {
            throw new RuntimeException("Tài khoản này đã bị khóa. Liên hệ quản trị viên hệ thống.");
        }

        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new RuntimeException("Tên đăng nhập hoặc mật khẩu không chính xác.");
        }

        // Cập nhật lần đăng nhập gần nhất
        user.setLastLogin(LocalDateTime.now());
        userRepository.save(user);

        String token = jwtUtil.generateToken(user.getUsername(), user.getRole(), user.getFullName());

        log.info("🔐 [AUTH] Đăng nhập thành công: {} ({})", user.getUsername(), user.getRole());

        return Map.of(
                "token", token,
                "username", user.getUsername(),
                "fullName", user.getFullName(),
                "role", user.getRole(),
                "email", user.getEmail() != null ? user.getEmail() : "",
                "lastLogin", user.getLastLogin().toString()
        );
    }

    /**
     * Lấy thông tin người dùng hiện tại từ JWT token.
     */
    public Map<String, Object> getCurrentUser(String token) {
        if (token == null || !jwtUtil.validateToken(token)) {
            throw new RuntimeException("Token không hợp lệ hoặc đã hết hạn.");
        }

        String username = jwtUtil.getUsername(token);
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("Không tìm thấy người dùng."));

        return Map.of(
                "username", user.getUsername(),
                "fullName", user.getFullName(),
                "role", user.getRole(),
                "email", user.getEmail() != null ? user.getEmail() : "",
                "lastLogin", user.getLastLogin() != null ? user.getLastLogin().toString() : ""
        );
    }
}
