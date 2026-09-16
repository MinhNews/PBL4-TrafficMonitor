package com.pbl4.trafficmonitor.controller;

import com.pbl4.trafficmonitor.service.ImageStorageService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/images")
@RequiredArgsConstructor
public class ImageController {
    private final ImageStorageService imageStorageService;

    @GetMapping("/{fileName}")
    public ResponseEntity<byte[]> getImage(@PathVariable String fileName) {
        try {
            byte[] data = imageStorageService.loadImage(fileName);
            return ResponseEntity.ok().contentType(MediaType.IMAGE_JPEG).body(data);
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }
}
