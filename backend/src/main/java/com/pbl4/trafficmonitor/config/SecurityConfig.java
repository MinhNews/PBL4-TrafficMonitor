package com.pbl4.trafficmonitor.config;

import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Cấu hình bảo vệ API bằng JWT.
 *
 * Quy tắc:
 * - /api/auth/login, /ws/** (WebSocket) và /error: mở (chưa có token).
 * - Toàn bộ /api/** còn lại: bắt buộc token hợp lệ (người dùng) hoặc X-AI-KEY (AI Service).
 * - Tài nguyên tĩnh khác: mở.
 *
 * Không dùng session (STATELESS) vì xác thực bằng Bearer token.
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    /** Không dùng tài khoản mặc định của Spring Security (hệ thống xác thực bằng JWT + bảng users). */
    @Bean
    public UserDetailsService userDetailsService() {
        return new InMemoryUserDetailsManager();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // REST API: tắt CSRF và các form login mặc định
            .csrf(AbstractHttpConfigurer::disable)
            .httpBasic(AbstractHttpConfigurer::disable)
            .formLogin(AbstractHttpConfigurer::disable)
            .logout(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // CORS preflight
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                // Đăng nhập + WebSocket + trang lỗi
                .requestMatchers("/api/auth/login", "/ws/**", "/error").permitAll()
                // Mọi API còn lại phải có token (hoặc X-AI-KEY của AI Service)
                .requestMatchers("/api/**").authenticated()
                .anyRequest().permitAll())
            // Trả JSON thay vì trang lỗi mặc định của Spring
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint((request, response, authException) ->
                        writeJson(response, HttpServletResponse.SC_UNAUTHORIZED,
                                "UNAUTHORIZED", "Thiếu hoặc sai token, vui lòng đăng nhập lại."))
                .accessDeniedHandler((request, response, accessDeniedException) ->
                        writeJson(response, HttpServletResponse.SC_FORBIDDEN,
                                "FORBIDDEN", "Tài khoản không có quyền thực hiện thao tác này.")))
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    private void writeJson(HttpServletResponse response, int status, String error, String message)
            throws java.io.IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"error\":\"" + error + "\",\"message\":\"" + message + "\"}");
    }
}
