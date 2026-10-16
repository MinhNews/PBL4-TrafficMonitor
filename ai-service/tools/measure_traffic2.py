import os
import sys
import time
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

VIDEO_PATH = os.path.join(BASE_DIR, "dataset", "traffic2.mp4")
OUTPUT_DIR = os.path.join(BASE_DIR, "tools", "debug_frames")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def compute_box_overlap(boxA, boxB):
    """Tính tỷ lệ phần diện tích boxA nằm trong boxB"""
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    areaA = max(1.0, (ax2 - ax1) * (ay2 - ay1))
    return inter / areaA

def run_measurement_300_frames():
    print(f"🎬 [MEASUREMENT] Bắt đầu đo 300 frame từ video: {VIDEO_PATH}")
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Không tìm thấy video tại: {VIDEO_PATH}")
        return

    # 1. Thử nghiệm chuẩn: YOLO11n @ 640 + ByteTrack
    print("\n--- [1] Đo YOLO11n (imgsz=640) trong 300 frame ---")
    model_11n = YOLO(os.path.join(BASE_DIR, "yolo11n.pt"))
    tracker = sv.ByteTrack(track_activation_threshold=0.25, lost_track_buffer=30, minimum_matching_threshold=0.8, frame_rate=30)

    cap = cv2.VideoCapture(VIDEO_PATH)
    frame_idx = 0
    frames_with_person = 0
    frames_person_no_moto_overlap = 0
    frames_zero_moto_with_person = 0
    total_persons_detected = 0
    persons_without_moto_overlap = 0

    track_classes = {} # {tracker_id: set(class_names)}
    saved_frames_count = 0

    t0 = time.time()

    while cap.isOpened() and frame_idx < 300:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        if frame.shape[0] > 720:
            scale = 720 / frame.shape[0]
            frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

        # Chạy inference
        results = model_11n.predict(frame, conf=0.25, imgsz=640, verbose=False)[0]
        
        persons = []
        motos = []
        det_boxes = []
        det_scores = []
        det_cls_ids = []
        det_cls_names = []

        raw_vis_frame = frame.copy() if saved_frames_count < 20 and frame_idx % 15 == 0 else None

        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = model_11n.names[cls_id]
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().tolist()

            det_boxes.append(xyxy)
            det_scores.append(conf)
            det_cls_ids.append(cls_id)
            det_cls_names.append(cls_name)

            if cls_name == "person":
                persons.append(xyxy)
            elif cls_name == "motorcycle":
                motos.append(xyxy)

            # Vẽ box thô cho 20 frame mẫu
            if raw_vis_frame is not None:
                color = (0, 165, 255) if cls_name == "person" else (255, 200, 0) if cls_name == "motorcycle" else (255, 0, 0)
                bx1, by1, bx2, by2 = map(int, xyxy)
                cv2.rectangle(raw_vis_frame, (bx1, by1), (bx2, by2), color, 2)
                cv2.putText(raw_vis_frame, f"{cls_name} {conf:.2f}", (bx1, max(15, by1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        if raw_vis_frame is not None:
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"raw_frame_{frame_idx}.jpg"), raw_vis_frame)
            saved_frames_count += 1

        # Cập nhật ByteTrack
        if len(det_boxes) > 0:
            det_sv = sv.Detections(
                xyxy=np.array(det_boxes),
                confidence=np.array(det_scores),
                class_id=np.array(det_cls_ids),
                data={"class_name": np.array(det_cls_names)}
            )
            tracks = tracker.update_with_detections(det_sv)
            if len(tracks) > 0 and tracks.tracker_id is not None:
                for tid, cname in zip(tracks.tracker_id, tracks.data["class_name"]):
                    tid = int(tid)
                    if tid not in track_classes:
                        track_classes[tid] = set()
                    track_classes[tid].add(str(cname))

        # Phân tích tương quan Person vs Motorcycle
        if len(persons) > 0:
            frames_with_person += 1
            total_persons_detected += len(persons)
            if len(motos) == 0:
                frames_zero_moto_with_person += 1

            has_isolated_person = False
            for p in persons:
                # Kiểm tra xem person này có chồng lấn với bất kỳ moto nào không (ngưỡng >= 15%)
                overlaps = [compute_box_overlap(p, m) for m in motos] if len(motos) > 0 else []
                max_ov = max(overlaps) if len(overlaps) > 0 else 0.0
                if max_ov < 0.15:
                    has_isolated_person = True
                    persons_without_moto_overlap += 1

            if has_isolated_person:
                frames_person_no_moto_overlap += 1

    t1 = time.time()
    total_time = t1 - t0
    fps_11n_640 = frame_idx / max(0.1, total_time)
    cap.release()

    # Thống kê track đổi lớp
    tracks_swapping_cls = 0
    for tid, cset in track_classes.items():
        if "person" in cset and "motorcycle" in cset:
            tracks_swapping_cls += 1

    print(f"\n📊 KẾT QUẢ ĐO 300 FRAME (YOLO11n @ imgsz=640):")
    print(f"  - Tổng số frame xử lý: {frame_idx}")
    print(f"  - Thời gian: {total_time:.2f}s | FPS trung bình: {fps_11n_640:.2f} FPS")
    print(f"  - Số frame có ít nhất 1 'person': {frames_with_person}/{frame_idx} ({frames_with_person/frame_idx*100:.1f}%)")
    print(f"  - Số frame có 'person' nhưng KHÔNG CÓ 'motorcycle' nào chồng lên: {frames_person_no_moto_overlap}/{frames_with_person} ({frames_person_no_moto_overlap/max(1, frames_with_person)*100:.1f}%)")
    print(f"  - Số frame có 'person' nhưng 0 'motorcycle' nào được phát hiện trong toàn khung: {frames_zero_moto_with_person}/{frames_with_person} ({frames_zero_moto_with_person/max(1, frames_with_person)*100:.1f}%)")
    print(f"  - Tổng số lượt bbox person phát hiện: {total_persons_detected}")
    print(f"  - Số lượt bbox person hoàn toàn không chồng lấn moto: {persons_without_moto_overlap} ({persons_without_moto_overlap/max(1, total_persons_detected)*100:.1f}%)")
    print(f"  - Tổng số track ID ByteTrack: {len(track_classes)}")
    print(f"  - Số track ID bị đổi lớp giữa 'person' và 'motorcycle': {tracks_swapping_cls}/{len(track_classes)} ({tracks_swapping_cls/max(1, len(track_classes))*100:.1f}%)")
    print(f"  - Đã lưu {saved_frames_count} ảnh bbox thô vào: {OUTPUT_DIR}")

    # 2. So sánh nhanh YOLO11n @ 960 và YOLO11s @ 640/960 trên 100 frame
    print("\n--- [2] So sánh YOLO11n vs YOLO11s trên 100 frame liên tiếp ---")
    configs = [
        ("yolo11n.pt", 640),
        ("yolo11n.pt", 960),
        ("yolo11s.pt", 640),
        ("yolo11s.pt", 960)
    ]

    for model_name, imgsz in configs:
        model_path = os.path.join(BASE_DIR, model_name)
        try:
            m = YOLO(model_path if os.path.exists(model_path) else model_name)
        except Exception as e:
            print(f"⚠️ Không thể tải {model_name}: {e}")
            continue

        cap = cv2.VideoCapture(VIDEO_PATH)
        f_cnt = 0
        m_frames = 0
        total_motos = 0
        t_start = time.time()

        while cap.isOpened() and f_cnt < 100:
            ret, frame = cap.read()
            if not ret:
                break
            f_cnt += 1
            if frame.shape[0] > 720:
                scale = 720 / frame.shape[0]
                frame = cv2.resize(frame, (int(frame.shape[1] * scale), 720))

            res = m.predict(frame, conf=0.25, imgsz=imgsz, verbose=False)[0]
            m_count = 0
            for box in res.boxes:
                cid = int(box.cls[0].item())
                if m.names[cid] == "motorcycle":
                    m_count += 1
            if m_count > 0:
                m_frames += 1
            total_motos += m_count

        t_end = time.time()
        fps_cfg = f_cnt / max(0.1, t_end - t_start)
        cap.release()

        print(f"  👉 Model: {model_name:10} | imgsz: {imgsz} | Tỉ lệ frame có moto: {m_frames}/{f_cnt} ({m_frames/f_cnt*100:.1f}%) | Tổng moto bboxes: {total_motos:3} | FPS: {fps_cfg:.2f}")

if __name__ == "__main__":
    run_measurement_300_frames()
