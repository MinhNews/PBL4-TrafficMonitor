package com.pbl4.trafficmonitor.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Kích hoạt Message Broker với tiền tố /topic để broadcast dữ liệu tới client
        config.enableSimpleBroker("/topic");
        // Tiền tố cho các message gửi từ client lên server (nếu có)
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // Đăng ký endpoint kết nối WebSocket là /ws
        // Cho phép Frontend React (localhost:5173) kết nối vào và hỗ trợ SockJS
        // fallback
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("http://localhost:5173", "http://localhost:3000")
                .withSockJS();
    }
}
