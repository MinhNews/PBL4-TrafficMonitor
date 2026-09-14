-- 1. Tạo Database
CREATE DATABASE IF NOT EXISTS traffic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE traffic_db;

-- 2. Bảng users (Tài khoản CSGT / Admin)
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'OFFICER',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- 3. Bảng regions (Khu vực / Ngã tư giám sát)
CREATE TABLE IF NOT EXISTS regions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    city VARCHAR(100) DEFAULT 'Đà Nẵng',
    district VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng cameras (Thông tin Camera kết nối)
CREATE TABLE IF NOT EXISTS cameras (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50),
    location_description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    stream_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- 5. Bảng vehicles (Danh mục phương tiện giao thông)
CREATE TABLE IF NOT EXISTS vehicles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(30) NOT NULL,
    name_vi VARCHAR(50),
    description VARCHAR(200)
);

-- 6. Bảng violations (Hồ sơ vi phạm - Bảng trọng tâm nhất)
CREATE TABLE IF NOT EXISTS violations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    camera_id BIGINT NOT NULL,
    vehicle_id BIGINT,
    violation_type VARCHAR(30) NOT NULL,
    vehicle_type VARCHAR(30),
    confidence DECIMAL(5, 4),
    status VARCHAR(20) DEFAULT 'PENDING',
    evidence_image_path VARCHAR(500),
    evidence_image_url VARCHAR(500),
    notes TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_by BIGINT,
    confirmed_at TIMESTAMP NULL,
    FOREIGN KEY (camera_id) REFERENCES cameras(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (confirmed_by) REFERENCES users(id)
);

-- 7. Bảng alerts (Lịch sử bắn cảnh báo còi/đèn tới ESP32)
CREATE TABLE IF NOT EXISTS alerts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    violation_id BIGINT NOT NULL,
    alert_type VARCHAR(30),
    mqtt_topic VARCHAR(100),
    mqtt_payload TEXT,
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(id)
);

-- 8. Bảng traffic_stats (Thống kê lưu lượng theo từng giờ)
CREATE TABLE IF NOT EXISTS traffic_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    camera_id BIGINT NOT NULL,
    stat_date DATE NOT NULL,
    stat_hour TINYINT NOT NULL,
    vehicle_count INT DEFAULT 0,
    motorcycle_count INT DEFAULT 0,
    car_count INT DEFAULT 0,
    violation_count INT DEFAULT 0,
    no_helmet_count INT DEFAULT 0,
    red_light_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_camera_date_hour (camera_id, stat_date, stat_hour),
    FOREIGN KEY (camera_id) REFERENCES cameras(id)
);

-- 9. Bảng notification_logs (Nhật ký thông báo push)
CREATE TABLE IF NOT EXISTS notification_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    violation_id BIGINT,
    channel VARCHAR(30),
    recipient VARCHAR(200),
    message TEXT,
    is_delivered BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(id)
);

-- 10. Bảng system_config (Cấu hình hệ thống lưu CSDL)
CREATE TABLE IF NOT EXISTS system_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value VARCHAR(500) NOT NULL,
    description VARCHAR(300),
    updated_by BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- ==========================================
-- CHÈN DỮ LIỆU KHỞI TẠO MẪU
-- ==========================================
INSERT INTO regions (name, city, district) VALUES ('Ngã tư Hòa Khánh', 'Đà Nẵng', 'Liên Chiểu');
INSERT INTO cameras (region_id, name, location_description, stream_url) VALUES (1, 'Camera 01 - Hòa Khánh', 'Góc Tây Bắc ngã tư', 'http://localhost:5000/video_feed');
INSERT INTO vehicles (type, name_vi) VALUES ('MOTORCYCLE', 'Xe máy'), ('CAR', 'Ô tô'), ('TRUCK', 'Xe tải'), ('BUS', 'Xe buýt');
INSERT INTO users (username, password, full_name, role) VALUES ('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lh8i', 'Admin Nhóm 3', 'ADMIN');
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('ai.confidence.threshold', '0.85', 'Ngưỡng độ tin cậy tối thiểu của AI'),
    ('alert.beep.times', '3', 'Số lần còi kêu khi có vi phạm'),
    ('traffic.light.red.duration', '15', 'Thời gian đèn đỏ (giây)'),
    ('traffic.light.green.duration', '15', 'Thời gian đèn xanh (giây)'),
    ('traffic.light.yellow.duration', '3', 'Thời gian đèn vàng (giây)');
