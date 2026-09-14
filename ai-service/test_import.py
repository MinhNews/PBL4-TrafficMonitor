import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("🔍 Testing imports...")

import torch
print(f"✅ PyTorch: {torch.__version__} | GPU: {torch.cuda.is_available()}")

from transformers import DetrForObjectDetection, DetrImageProcessor
print("✅ Transformers DETR: OK")

from transformers import ViTForImageClassification, ViTImageProcessor
print("✅ Transformers ViT: OK")

import cv2
print(f"✅ OpenCV: {cv2.__version__}")

import supervision as sv
print(f"✅ Supervision: {sv.__version__}")

import flask
print(f"✅ Flask: {flask.__version__}")

import paho.mqtt.client
print("✅ MQTT paho: OK")

import requests
print(f"✅ Requests: {requests.__version__}")

print("\n🎉 TẤT CẢ IMPORT THÀNH CÔNG! Môi trường AI sẵn sàng.")
