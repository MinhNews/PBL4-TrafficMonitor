import os
import sys
import time
import numpy as np
import cv2

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

import config
from core.entity import TrafficEntity
from core.tracker_manager import TrafficTrackerManager
from core.violation_engine import ViolationEngine
from services.vit_worker import AsyncViTWorker
from detectors.helmet_classifier import HelmetClassifier

class MockBackend:
    def __init__(self):
        self.violations = []
        self.flows = []

    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))

    def send_traffic_flow(self, count, vehicle_type):
        self.flows.append((count, vehicle_type))

def test_suite():
    print("=" * 70)
    print("--- CHAY BO KIEM THU CAC TIEU CHUAN NGHIEP VU (NHOM A, B, C, D) ---")
    print("=" * 70)

    results = {}
    backend = MockBackend()
    v_engine = ViolationEngine(backend)
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    stop_line_y = 468

    # TEST 1: Xe dừng sát vạch suốt đèn đỏ: không biên bản, không tính lưu lượng
    car_stop = TrafficEntity(1, [100, 470, 160, 530], "car", 0.9, stop_line_y=stop_line_y)
    # Rung lắc pixel nhiều frame sát vạch dừng
    jitter_boxes = [
        [100, 469.0, 160, 529.0],
        [100, 470.5, 160, 530.5],
        [100, 468.2, 160, 528.2],
        [100, 469.8, 160, 529.8],
    ]
    t1_violation = False
    t1_flow = False
    for jbox in jitter_boxes:
        car_stop.update(jbox, "car", 0.9, stop_line_y=stop_line_y)
        if v_engine.check_red_light_violation(car_stop, "RED", stop_line_y, dummy_frame):
            t1_violation = True
        if v_engine.check_traffic_flow(car_stop, stop_line_y):
            t1_flow = True

    results["1. Xe dừng sát vạch suốt đèn đỏ: không biên bản, không tính lưu lượng"] = (
        not t1_violation and not t1_flow and len(backend.violations) == 0 and len(backend.flows) == 0
    )

    # TEST 2: Xe chạy qua vạch lúc đèn đỏ: đúng một biên bản
    car_cross = TrafficEntity(2, [200, 475, 260, 535], "car", 0.9, stop_line_y=stop_line_y)
    # Frame 1: đang ở dưới vạch (leading_edge = 475 >= 468)
    car_cross.update([200, 475, 260, 535], "car", 0.9, stop_line_y=stop_line_y)
    v_engine.check_red_light_violation(car_cross, "RED", stop_line_y, dummy_frame)
    # Frame 2: cắt qua vạch (leading_edge = 450 < 468)
    car_cross.update([200, 450, 260, 510], "car", 0.9, stop_line_y=stop_line_y)
    v2_first = v_engine.check_red_light_violation(car_cross, "RED", stop_line_y, dummy_frame)
    # Frame 3: tiếp tục di chuyển sâu hơn qua vạch (vẫn đèn ĐỎ)
    car_cross.update([200, 430, 260, 490], "car", 0.9, stop_line_y=stop_line_y)
    v2_second = v_engine.check_red_light_violation(car_cross, "RED", stop_line_y, dummy_frame)

    # Đếm số biên bản gửi đi cho xe 2
    car_2_violations = [v for v in backend.violations if v[0] == "RED_LIGHT_CROSS"]
    results["2. Xe chạy qua vạch lúc đèn đỏ: đúng một biên bản"] = (
        v2_first is True and len(car_2_violations) == 1 and v_engine.violation_count == 1
    )

    # TEST 3: Xe chở 2-3 người, một người không mũ: đúng một biên bản cho xe đó
    rider_1 = TrafficEntity(11, [300, 400, 330, 460], "person", 0.85, stop_line_y=stop_line_y)
    rider_1.set_role("rider", moto_id=10) # Ngồi trên xe máy 10

    rider_2 = TrafficEntity(12, [310, 420, 340, 480], "person", 0.80, stop_line_y=stop_line_y)
    rider_2.set_role("rider", moto_id=10) # Cũng ngồi trên xe máy 10

    # Người 1 vi phạm không đội mũ
    v_engine.process_helmet_result(rider_1, is_no_helmet=True, conf=0.92, clean_frame=dummy_frame)
    # Người 2 cũng không đội mũ ngay sau đó (cùng xe máy 10)
    v_engine.process_helmet_result(rider_2, is_no_helmet=True, conf=0.88, clean_frame=dummy_frame)

    moto_10_violations = [v for v in backend.violations if v[0] == "NO_HELMET"]
    results["3. Xe chở 2-3 người, một người không mũ: đúng một biên bản cho xe đó"] = (
        len(moto_10_violations) == 1
    )

    # TEST 4: Người đi bộ băng qua vạch lúc đèn đỏ: không biên bản, không tính lưu lượng
    pedestrian = TrafficEntity(4, [50, 480, 80, 540], "person", 0.9, stop_line_y=stop_line_y)
    pedestrian.set_role("pedestrian")
    # Người đi bộ cắt qua vạch dừng
    pedestrian.update([50, 450, 80, 510], "person", 0.9, stop_line_y=stop_line_y)
    t4_viol = v_engine.check_red_light_violation(pedestrian, "RED", stop_line_y, dummy_frame)
    t4_flow = v_engine.check_traffic_flow(pedestrian, stop_line_y)

    results["4. Người đi bộ băng qua vạch lúc đèn đỏ: không biên bản, không tính lưu lượng"] = (
        not t4_viol and not t4_flow
    )

    # TEST 5: Xe ngược chiều cắt vạch lúc đèn đỏ: không biên bản
    car_reverse = TrafficEntity(5, [500, 440, 560, 500], "car", 0.9, stop_line_y=stop_line_y)
    # Đi từ trên xuống dưới (ngược chiều: 440 -> 475)
    car_reverse.update([500, 475, 560, 535], "car", 0.9, stop_line_y=stop_line_y)
    t5_viol = v_engine.check_red_light_violation(car_reverse, "RED", stop_line_y, dummy_frame)

    results["5. Xe ngược chiều cắt vạch lúc đèn đỏ: không biên bản"] = (
        not t5_viol
    )

    # TEST 6: Video lặp vòng thứ hai: số liệu và trạng thái ViT sạch, không thừa kế từ vòng trước
    tracker_mgr = TrafficTrackerManager()
    helmet_clf = HelmetClassifier()
    vit_worker = AsyncViTWorker(helmet_clf, v_engine)

    # Thêm dữ liệu giả lập
    tracker_mgr.entities[99] = car_stop
    tracker_mgr.riders_map[99] = 10
    v_engine.passed_vehicles.add(99)
    vit_worker.track_status[99] = {"is_no_helmet": True, "conf": 0.9}
    helmet_clf.history[99] = 5

    # Thực hiện Reset toàn hệ thống
    tracker_mgr.reset()
    v_engine.reset()
    vit_worker.reset()

    results["6. Video lặp vòng thứ hai: số liệu và trạng thái ViT sạch, không thừa kế từ vòng trước"] = (
        len(tracker_mgr.entities) == 0 and
        len(tracker_mgr.riders_map) == 0 and
        len(tracker_mgr.rider_history) == 0 and
        len(v_engine.violating_vehicles) == 0 and
        len(v_engine.passed_vehicles) == 0 and
        len(v_engine.reported_violations) == 0 and
        v_engine.violation_count == 0 and
        len(vit_worker.track_status) == 0 and
        len(helmet_clf.history) == 0
    )

    print("\n=== KET QUA KIEM THU TUNG DONG (DAT / KHONG DAT): ===")
    all_passed = True
    for item, passed in results.items():
        status = "[DAT]" if passed else "[KHONG DAT]"
        if not passed:
            all_passed = False
        print(f"  {status} {item}")

    print("\n" + "=" * 70)
    if all_passed:
        print(">>> TAT CA 6 TIEU CHUAN NGHIEP VU DA DAT 100%!")
    else:
        print(">>> Co tieu chuan chua dat!")
    print("=" * 70)
    vit_worker.stop()


if __name__ == "__main__":
    test_suite()
