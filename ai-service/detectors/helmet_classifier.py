import os, sys, cv2, torch
import numpy as np
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
                print(f"[ViT] Dang nap model tu: {self.model_dir}...")
                self.processor = ViTImageProcessor.from_pretrained(self.model_dir)
                self.model = ViTForImageClassification.from_pretrained(self.model_dir).to(self.device)
                self.model.eval()
                self.is_real_model = True
                
                # C5: Đọc id2label từ model để xác định chính xác chỉ số lớp no_helmet
                self.no_helmet_idx = 1
                if hasattr(self.model.config, "id2label") and self.model.config.id2label:
                    id2label = self.model.config.id2label
                    print(f"[ViT] id2label: {id2label}")
                    for idx, label in id2label.items():
                        lbl = str(label).lower()
                        if "no" in lbl or "without" in lbl or "none" in lbl:
                            self.no_helmet_idx = int(idx)
                            break
                print(f"[ViT] Ready tren {self.device.upper()} | no_helmet_idx = {self.no_helmet_idx}")
            except Exception as e:
                print(f"[ViT Warning] Loi nap ViT model: {e}. Dung Fallback mode.")
                self.no_helmet_idx = 1
        else:
            print(f"[ViT Warning] Khong tim thay weights tai '{self.model_dir}'. Dung Fallback mode.")
            self.no_helmet_idx = 1


    def reset(self):
        """Làm mới toàn bộ lịch sử khi video tua lại loop (C2)"""
        self.history.clear()

    def predict_head(self, head_crop_bgr):
        """
        Nhận vào ảnh cắt vùng đầu (Head Crop - BGR từ OpenCV).
        Trả về: (is_no_helmet: bool, confidence: float)
        """
        if head_crop_bgr is None or head_crop_bgr.size == 0:
            return False, 0.0

        # TRƯỜNG HỢP 1: Chạy mô hình ViT thật (C5: dùng trực tiếp xác suất lớp no_helmet)
        if self.is_real_model:
            rgb = cv2.cvtColor(head_crop_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            inputs = self.processor(images=pil_img, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]
                p_no_helmet = float(probs[self.no_helmet_idx].item())

            # So sánh trực tiếp xác suất lớp no_helmet với ngưỡng
            is_no_helmet = (p_no_helmet >= config.VIT_CONFIDENCE_THRESHOLD)
            return is_no_helmet, round(p_no_helmet, 4)

        # TRƯỜNG HỢP 2: Chế độ Fallback thông minh (khi đang chờ train trên Colab)
        gray = cv2.cvtColor(head_crop_bgr, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        is_no_helmet = (brightness > 100) # Giả lập phát hiện đầu trần
        conf = 0.88
        return is_no_helmet, conf

    def update_and_check(self, tracker_id, head_crop_bgr):
        """
        Cơ chế Time-Window chống báo giả:
        Phải phát hiện không đội mũ >= NO_HELMET_FRAMES_REQUIRED mới khẳng định vi phạm!
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

    def cleanup_history(self, expired_ids):
        """Chỉ xóa lịch sử của các xe đã hết hạn 5 giây (C4)"""
        for tid in list(expired_ids):
            self.history.pop(tid, None)

