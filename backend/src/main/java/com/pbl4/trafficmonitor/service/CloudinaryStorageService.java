package com.pbl4.trafficmonitor.service;

import com.cloudinary.Cloudinary;
import com.cloudinary.utils.ObjectUtils;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@Service
@Slf4j
public class CloudinaryStorageService {

    @Value("${cloudinary.cloud-name}")
    private String cloudName;

    @Value("${cloudinary.api-key}")
    private String apiKey;

    @Value("${cloudinary.api-secret}")
    private String apiSecret;

    @Value("${cloudinary.folder:pbl4_traffic_violations}")
    private String folderName;

    private Cloudinary cloudinary;

    @PostConstruct
    public void init() {
        // Khởi tạo đối tượng Cloudinary với thông tin tài khoản thật của Minh
        Map<String, String> config = new HashMap<>();
        config.put("cloud_name", cloudName);
        config.put("api_key", apiKey);
        config.put("api_secret", apiSecret);
        this.cloudinary = new Cloudinary(config);
        log.info("☁️ Khởi tạo Cloudinary thành công với Cloud Name: [{}] | Thư mục: [{}]", cloudName, folderName);
    }

    /**
     * Upload ảnh bằng chứng từ chuỗi Base64 lên Cloudinary
     * 
     * @param base64Data Chuỗi ảnh Base64 gửi từ camera AI
     * @return Đường link ảnh HTTPS trên Cloudinary (hoặc null nếu lỗi)
     */
    public String uploadBase64Image(String base64Data) {
        if (base64Data == null || base64Data.trim().isEmpty()) {
            return null;
        }

        try {
            // 1. Cắt bỏ header "data:image/jpeg;base64," nếu AI gửi kèm
            String cleanBase64 = base64Data;
            if (cleanBase64.contains(",")) {
                cleanBase64 = cleanBase64.substring(cleanBase64.indexOf(",") + 1);
            }

            // 2. Decode chuỗi Base64 thành mảng byte dữ liệu ảnh
            byte[] imageBytes = Base64.getDecoder().decode(cleanBase64.trim());

            // 3. Cấu hình tham số upload: gom vào thư mục riêng pbl4_traffic_violations
            Map<String, Object> params = ObjectUtils.asMap(
                    "folder", folderName,
                    "resource_type", "image");

            // 4. Upload lên Cloudinary
            Map uploadResult = cloudinary.uploader().upload(imageBytes, params);
            String secureUrl = (String) uploadResult.get("secure_url");

            log.info("✅ Upload ảnh vi phạm lên Cloudinary thành công: {}", secureUrl);
            return secureUrl;

        } catch (Exception e) {
            log.error("❌ Lỗi khi upload ảnh lên Cloudinary: {}", e.getMessage());
            return null; // Trả về null để không làm crash luồng lưu dữ liệu vi phạm
        }
    }
}
