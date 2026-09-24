import os, sys
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from transformers import ViTForImageClassification, ViTImageProcessor
from sklearn.metrics import classification_report
import numpy as np

# 1. KHỞI TẠO PROCESSOR & TIỀN XỬ LÝ ẢNH
MODEL_NAME = "google/vit-base-patch16-224"
print(f"⏳ Đang khởi tạo ViT Image Processor từ '{MODEL_NAME}'...")
processor = ViTImageProcessor.from_pretrained(MODEL_NAME)

# Data Augmentation cho tập Train (tạo thêm biến thể ảnh thực tế)
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=processor.image_mean, std=processor.image_std)
])

# Tiền xử lý cho tập Validation (không xoay hay đổi màu)
val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=processor.image_mean, std=processor.image_std)
])

def train():
    data_dir = "dataset/helmet_data"
    train_dir = os.path.join(data_dir, "train")
    val_dir = os.path.join(data_dir, "val")

    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        print(f"❌ Chưa tìm thấy dữ liệu tại '{data_dir}'. Vui lòng giải nén tập dữ liệu theo cấu trúc ImageFolder!")
        return

    # 2. NẠP DỮ LIỆU BẰNG IMAGEFOLDER
    print("📂 Đang nạp tập dữ liệu ảnh...")
    train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

    print(f"   + Số ảnh huấn luyện: {len(train_dataset)} ({train_dataset.classes})")
    print(f"   + Số ảnh kiểm thử: {len(val_dataset)}")

    # 3. KHỞI TẠO MÔ HÌNH ViT VỚI 2 LỚP: HELMET vs NO_HELMET
    id2label = {0: "helmet", 1: "no_helmet"}
    label2id = {"helmet": 0, "no_helmet": 1}

    model = ViTForImageClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"🚀 Bắt đầu huấn luyện Vision Transformer trên thiết bị: {device.upper()}!")

    # 4. OPTIMIZER & LOSS
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()

    # 5. VÒNG LẶP HUẤN LUYỆN (5 EPOCHS)
    best_val_acc = 0.0
    output_dir = "models/vit_helmet_best"
    os.makedirs("models", exist_ok=True)

    for epoch in range(5):
        # A. TRAIN
        model.train()
        total_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs.logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        # B. EVALUATE TRÊN TẬP VAL
        model.eval()
        correct, total = 0, 0
        all_preds, all_labels = [], []
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                preds = model(images).logits.argmax(dim=-1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        val_acc = correct / total if total > 0 else 0
        avg_loss = total_loss / len(train_loader)
        print(f"Epoch [{epoch+1}/5] - Train Loss: {avg_loss:.4f} | Val Accuracy: {val_acc*100:.2f}%")

        # Lưu lại checkpoint tốt nhất
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            model.save_pretrained(output_dir)
            processor.save_pretrained(output_dir)
            print(f"💾 Đã lưu mô hình tốt nhất đạt Accuracy: {best_val_acc*100:.2f}% tại '{output_dir}'!")

    # 6. ĐÁNH GIÁ CHÍNH THỨC TRÊN TẬP TEST ĐỘC LẬP (DÀNH CHO BÁO CÁO ĐỒ ÁN)
    test_dir = os.path.join(data_dir, "test")
    if os.path.exists(test_dir):
        print("\n🎓 ĐANG CHẤM ĐIỂM TRÊN TẬP TEST ĐỘC LẬP (FINAL TEST EVALUATION)...")
        test_dataset = datasets.ImageFolder(test_dir, transform=val_transform)
        test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

        best_model = ViTForImageClassification.from_pretrained(output_dir).to(device)
        best_model.eval()

        test_correct, test_total = 0, 0
        all_test_preds, all_test_labels = [], []
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                preds = best_model(images).logits.argmax(dim=-1)
                test_correct += (preds == labels).sum().item()
                test_total += labels.size(0)
                all_test_preds.extend(preds.cpu().numpy())
                all_test_labels.extend(labels.cpu().numpy())

        test_acc = test_correct / test_total if test_total > 0 else 0
        print(f"🏆 ĐỘ CHÍNH XÁC TẬP TEST (TEST ACCURACY): {test_acc*100:.2f}%\n")
        print("📊 BÁO CÁO ĐÁNH GIÁ MÔ HÌNH (CLASSIFICATION REPORT PHỤC VỤ VIẾT BÁO CÁO ĐỒ ÁN):")
        print(classification_report(all_test_labels, all_test_preds, target_names=train_dataset.classes))
    else:
        print("\n📊 BÁO CÁO ĐÁNH GIÁ MÔ HÌNH TRÊN TẬP VALIDATION:")
        if all_labels:
            print(classification_report(all_labels, all_preds, target_names=train_dataset.classes))

if __name__ == "__main__":
    train()

