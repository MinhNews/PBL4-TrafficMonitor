import { Client } from '@stomp/stompjs';
import SockJS from 'sockjs-client';

export function connectWebSocket(onViolationReceived) {
  const client = new Client({
    // Đường dẫn bắt tay WebSocket tới Backend Spring Boot
    webSocketFactory: () => new SockJS('http://localhost:8080/ws'),
    reconnectDelay: 5000,
    onConnect: () => {
      console.log('⚡ Đã kết nối WebSocket STOMP với Backend!');
      
      // Đăng ký nhận thông báo vi phạm thời gian thực từ channel /topic/violations
      client.subscribe('/topic/violations', (message) => {
        const newViolation = JSON.parse(message.body);
        console.log('🚨 Có ca vi phạm mới:', newViolation);
        onViolationReceived(newViolation);
      });
    },
    onStompError: (frame) => {
      console.error('❌ Lỗi STOMP:', frame.headers['message']);
    }
  });

  client.activate();
  return client;
}