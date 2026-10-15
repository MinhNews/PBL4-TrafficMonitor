import os, sys, cv2, torch
import numpy as np
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "models", "vit_helmet_best"))

class HelmetClassifier:
    def __init__(self, model_dir=None):
        """
        Khởi tạo bộ phân loại Mũ bảo hiểm Vision Transformer (ViT)
        - model_dir: Thư mục chứa trọng số mô hình sau khi train trên Google Colab
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.history = {} # Lưu lịch sử đếm frame: {tracker_id: số_frame_không_đội_mũ}
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.is_real_model = False

        if os.path.exists(self.model_dir) and (
            os.path.exists(os.path.join(self.model_dir, "model.safetensors")) or 
            os.path.exists(os.path.join(self.model_dir, "pytorch_model.bin"))
        ):
            try:
                from transformers import ViTForImageClassification, ViTImageProcessor
                print(f"[ViT] Đang nạp mô hình mũ bảo hiểm từ: {self.model_dir}...")
                self.processor = ViTImageProcessor.from_pretrained(self.model_dir)
                self.model = ViTForImageClassification.from_pretrained(self.model_dir).to(self.device)
                self.model.eval()
                self.is_real_model = True
                print(f"[ViT] Mô hình ViT sẵn sàng trên thiết bị: {self.device.upper()}!")
            except Exception as e:
                print(f"[ViT Warning] Không thể nạp ViT model: {e}. Dùng Fallback mode.")
        else:
            print(f"[ViT Warning] Không tìm thấy weights tại '{self.model_dir}'. Dùng Fallback mode.")

    def predict_head(self, head_crop_bgr):
        """
        Nhận vào ảnh cắt vùng đầu (Head Crop - BGR từ OpenCV).
        Trả về: (is_no_helmet: bool, confidence: float)
        """
        if head_crop_bgr is None or head_crop_bgr.size == 0:
            return False, 0.0

        # TRƯỜNG HỢP 1: Chạy mô hình ViT thật (đã train)
        if self.is_real_model:
            rgb = cv2.cvtColor(head_crop_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            inputs = self.processor(images=pil_img, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]
                pred_id = probs.argmax().item()
                conf = probs[pred_id].item()

            # ID 0: helmet, ID 1: no_helmet (ngưỡng tin cậy >= config.VIT_CONFIDENCE_THRESHOLD)
            is_no_helmet = (pred_id == 1 and conf >= config.VIT_CONFIDENCE_THRESHOLD)
            return is_no_helmet, round(conf, 4)

        # TRƯỜNG HỢP 2: Chế độ Fallback thông minh (khi đang chờ train trên Colab)
        # Phân tích sơ bộ màu sắc/độ sáng của vùng đầu
        gray = cv2.cvtColor(head_crop_bgr, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        is_no_helmet = (brightness > 100) # Giả lập phát hiện đầu trần
        conf = 0.88
        return is_no_helmet, conf

    def update_and_check(self, tracker_id, head_crop_bgr):
        """
        Cơ chế Time-Window chống báo giả:
        Phải phát hiện không đội mũ >= NO_HELMET_FRAMES_REQUIRED (5 frame) mới khẳng định vi phạm!
        Trả về: (violation_confirmed: bool, confidence: float)
        """
        is_no_helmet, conf = self.predict_head(head_crop_bgr)

        if tracker_id not in self.history:
            self.history[tracker_id] = 0

        if is_no_helmet:
            self.history[tracker_id] = min(10, self.history[tracker_id] + 1)
        else:
            self.history[tracker_id] = max(0, self.history[tracker_id] - 2)

        # Kiểm tra ngưỡng frame liên tiếp từ config (mặc định 3 frame)
        required_frames = getattr(config, "NO_HELMET_FRAMES_REQUIRED", 3)
        if self.history[tracker_id] >= required_frames:
            return True, conf

        return False, conf

    def cleanup_history(self, active_tr_ids):
        """Xóa lịch sử của các xe đã biến mất để tránh rò rỉ RAM"""
        stale = [tid for tid in self.history if tid not in active_tr_ids]
        for tid in stale:
            self.history.pop(tid, None)
