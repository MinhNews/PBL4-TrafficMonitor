package com.pbl4.trafficmonitor.config;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponse;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * B3: Bộ xử lý lỗi tập trung cho toàn bộ REST API.
 *
 * Trước đây không có @RestControllerAdvice nên mọi exception không được bắt sẽ rơi vào
 * trang lỗi mặc định của Spring: trả về HTML kèm stack trace (lộ tên class, đường dẫn file,
 * cấu trúc DB...) và frontend phải parse HTML thay vì JSON.
 *
 * Sau khi thêm class này:
 *  - Mọi lỗi đều trả JSON thống nhất: { timestamp, status, error, message, path }
 *  - Lỗi nghiệp vụ (RuntimeException có message) -> 400 kèm câu giải thích tiếng Việt
 *  - Lỗi hệ thống thật (NullPointerException, lỗi DB...) -> 500 với thông báo chung chung,
 *    stack trace chỉ ghi vào log của server, KHÔNG gửi ra client
 *  - Các lỗi chuẩn của Spring (404, 405, 415...) vẫn giữ đúng mã HTTP như cũ
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /** Tham số/định dạng không hợp lệ do phía client gửi lên. */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgument(IllegalArgumentException ex,
                                                                     HttpServletRequest request) {
        log.warn("Yêu cầu không hợp lệ [{} {}]: {}", request.getMethod(), request.getRequestURI(), ex.getMessage());
        return build(HttpStatus.BAD_REQUEST, ex.getMessage(), request);
    }

    /**
     * Lỗi nghiệp vụ: service ném RuntimeException với message tiếng Việt
     * (vd: "Không tìm thấy vi phạm ID: 5", "Camera không tồn tại").
     * Chỉ coi là 400 khi có message; lỗi không có message (NPE...) rơi xuống handler 500.
     */
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleRuntime(RuntimeException ex,
                                                             HttpServletRequest request) {
        String message = ex.getMessage();
        if (message == null || message.isBlank()) {
            return handleUnexpected(ex, request);
        }
        log.warn("Nghiệp vụ từ chối [{} {}]: {}", request.getMethod(), request.getRequestURI(), message);
        return build(HttpStatus.BAD_REQUEST, message, request);
    }

    /** Chốt chặn cuối cùng: không bao giờ để stack trace lọt ra ngoài. */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleUnexpected(Exception ex,
                                                                HttpServletRequest request) {
        // Tôn trọng mã HTTP mà Spring đã gán (404 cho URL sai, 405 cho sai method, ...)
        if (ex instanceof ErrorResponse errorResponse) {
            String detail = errorResponse.getBody().getDetail();
            return build(HttpStatus.valueOf(errorResponse.getStatusCode().value()), detail, request);
        }

        log.error("Lỗi không mong đợi [{} {}]", request.getMethod(), request.getRequestURI(), ex);
        return build(HttpStatus.INTERNAL_SERVER_ERROR,
                "Lỗi hệ thống. Vui lòng thử lại hoặc liên hệ quản trị viên.", request);
    }

    private ResponseEntity<Map<String, Object>> build(HttpStatus status, String message,
                                                      HttpServletRequest request) {
        String safeMessage = (message == null || message.isBlank())
                ? status.getReasonPhrase()
                : message;

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("status", status.value());
        // Giữ khoá "error" để tương thích với các màn hình frontend đang đọc data.error
        body.put("error", safeMessage);
        body.put("message", safeMessage);
        body.put("path", request.getRequestURI());
        return ResponseEntity.status(status).body(body);
    }
}
