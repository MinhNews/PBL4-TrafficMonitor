import os
import sys
import glob
import cv2
import torch
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from detectors.helmet_classifier import HelmetClassifier

clf = HelmetClassifier()

test_dir = os.path.join(BASE_DIR, "dataset", "helmet_data", "test")
helmet_imgs = glob.glob(os.path.join(test_dir, "helmet", "*.*"))[:15]
no_helmet_imgs = glob.glob(os.path.join(test_dir, "no_helmet", "*.*"))[:15]

print("\n--- TEST TRÊN 15 ẢNH 'HELMET' (CÓ ĐỘI MŨ THẬT) ---")
for p in helmet_imgs:
    img = cv2.imread(p)
    if img is None: continue
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    inputs = clf.processor(images=Image.fromarray(rgb), return_tensors="pt").to(clf.device)
    with torch.no_grad():
        probs = torch.softmax(clf.model(**inputs).logits, dim=-1)[0]
    p0, p1 = probs[0].item(), probs[1].item()
    print(f"File: {os.path.basename(p):20} | P(index 0)={p0:.3f} | P(index 1)={p1:.3f} -> Argmax={probs.argmax().item()}")

print("\n--- TEST TRÊN 15 ẢNH 'NO_HELMET' (KHÔNG ĐỘI MŨ THẬT) ---")
for p in no_helmet_imgs:
    img = cv2.imread(p)
    if img is None: continue
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    inputs = clf.processor(images=Image.fromarray(rgb), return_tensors="pt").to(clf.device)
    with torch.no_grad():
        probs = torch.softmax(clf.model(**inputs).logits, dim=-1)[0]
    p0, p1 = probs[0].item(), probs[1].item()
    print(f"File: {os.path.basename(p):20} | P(index 0)={p0:.3f} | P(index 1)={p1:.3f} -> Argmax={probs.argmax().item()}")
