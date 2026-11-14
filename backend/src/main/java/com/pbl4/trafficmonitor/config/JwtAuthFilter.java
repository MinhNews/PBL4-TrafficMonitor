package com.pbl4.trafficmonitor.config;

import com.pbl4.trafficmonitor.util.JwtUtil;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Trạm gác JWT cho toàn bộ API.
 * - Request có header "Authorization: Bearer <token>" hợp lệ -> gắn quyền ROLE_<role> vào SecurityContext.
 * - Request nội bộ từ AI Service có header "X-AI-KEY" đúng -> cho vào với quyền ROLE_AI
 *   (AI Service không có tài khoản người dùng nên dùng khoá chia sẻ).
 * - Còn lại: để SecurityConfig trả 401 (chưa đăng nhập) hoặc 403 (sai quyền).
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    @Value("${app.ai.api-key:pbl4-nhom3-ai-service-2026}")
    private String aiApiKey;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        // 1. Khoá nội bộ cho AI Service (POST vi phạm, POST lưu lượng)
        String aiKey = request.getHeader("X-AI-KEY");
        if (aiApiKey != null && !aiApiKey.isBlank() && aiApiKey.equals(aiKey)) {
            var auth = new UsernamePasswordAuthenticationToken(
                    "ai-service", null, List.of(new SimpleGrantedAuthority("ROLE_AI")));
            SecurityContextHolder.getContext().setAuthentication(auth);
            filterChain.doFilter(request, response);
            return;
        }

        // 2. JWT của người dùng
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            try {
                if (jwtUtil.validateToken(token)) {
                    String role = jwtUtil.getRole(token);
                    var authorities = List.of(new SimpleGrantedAuthority(
                            "ROLE_" + (role == null || role.isBlank() ? "USER" : role.toUpperCase())));
                    var auth = new UsernamePasswordAuthenticationToken(
                            jwtUtil.getUsername(token), null, authorities);
                    SecurityContextHolder.getContext().setAuthentication(auth);
                }
            } catch (Exception e) {
                log.debug("Bỏ qua token không hợp lệ: {}", e.getMessage());
            }
        }

        filterChain.doFilter(request, response);
    }
}
