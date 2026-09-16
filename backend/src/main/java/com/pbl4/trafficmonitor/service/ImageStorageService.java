package com.pbl4.trafficmonitor.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.io.IOException;
import java.nio.file.*;
import java.util.Base64;
import java.util.UUID;

@Service
public class ImageStorageService {

    @Value("${app.upload.dir:./uploads/evidence}")
    private String uploadDir;

    public String saveBase64Image(String base64Data) throws IOException {
        if (base64Data == null || base64Data.trim().isEmpty()) return null;

        String base64Image = base64Data;
        if (base64Data.contains(",")) {
            base64Image = base64Data.split(",")[1];
        }

        byte[] imageBytes = Base64.getDecoder().decode(base64Image);
        Path uploadPath = Paths.get(uploadDir);
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }

        String fileName = UUID.randomUUID().toString() + ".jpg";
        Path filePath = uploadPath.resolve(fileName);
        Files.write(filePath, imageBytes);
        return fileName;
    }

    public byte[] loadImage(String fileName) throws IOException {
        Path filePath = Paths.get(uploadDir).resolve(fileName);
        if (!Files.exists(filePath)) {
            throw new RuntimeException("Không tìm thấy file: " + fileName);
        }
        return Files.readAllBytes(filePath);
    }
}
