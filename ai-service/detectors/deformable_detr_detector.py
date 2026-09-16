import torch
import cv2
import numpy as np
from transformers import DeformableDetrForObjectDetection, DeformableDetrImageProcessor
from PIL import Image
import sys, os

# Thêm thư mục cha vào đường dẫn để import config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

class DeformableDetrDetector:
    def __init__(self):
        print("⏳ Đang tải mô hình Deformable DETR từ HuggingFace (SenseTime/deformable-detr)...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = DeformableDetrImageProcessor.from_pretrained("SenseTime/deformable-detr")
        self.model = DeformableDetrForObjectDetection.from_pretrained("SenseTime/deformable-detr").to(self.device)
        self.model.eval()
        print(f"✅ Deformable DETR đã sẵn sàng! Thiết bị xử lý: {self.device.upper()}")

    def detect(self, frame_bgr):
        """
        Nhận vào 1 frame hình từ OpenCV (BGR)
        Trả về danh sách đối tượng: [
            {'box': [x1, y1, x2, y2], 'class_name': 'motorcycle', 'score': 0.95}, ...
        ]
        """
        # Bước 1: Đổi hệ màu BGR sang RGB và chuyển sang PIL Image
        image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)

        # Bước 2: Chuẩn hóa ảnh đầu vào cho PyTorch Tensor
        inputs = self.processor(images=pil_img, return_tensors="pt").to(self.device)

        # Bước 3: Chạy suy luận (không tính gradient để tăng tốc)
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Bước 4: Hậu xử lý kết quả về kích thước khung hình gốc
        target_sizes = torch.tensor([pil_img.size[::-1]]).to(self.device)
        results = self.processor.post_process_object_detection(
            outputs,
            target_sizes=target_sizes,
            threshold=config.DETR_CONFIDENCE_THRESHOLD
        )[0]

        # Bước 5: Lọc các nhãn giao thông quan tâm (COCO: person, car, motorcycle, bus, truck)
        detections = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            class_id = label.item()
            if class_id in config.COCO_CLASSES_OF_INTEREST:
                box_coords = [round(i, 2) for i in box.tolist()] # [x1, y1, x2, y2]
                detections.append({
                    "box": box_coords,
                    "class_name": config.COCO_CLASSES_OF_INTEREST[class_id],
                    "score": round(score.item(), 4)
                })

        return detections
