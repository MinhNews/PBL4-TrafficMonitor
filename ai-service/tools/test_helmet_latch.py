import sys
import os
import cv2
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from core.entity import TrafficEntity
from core.violation_engine import ViolationEngine
from services.vit_worker import AsyncViTWorker
from detectors.helmet_classifier import HelmetClassifier

class MockBackend:
    def __init__(self):
        self.violations = []
    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))
    def send_traffic_flow(self, count, vehicle_type):
        pass

def test_helmet_latch():
    backend = MockBackend()
    v_engine = ViolationEngine(backend)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Rider ban đầu chưa vi phạm
    rider = TrafficEntity(15, [200, 200, 250, 320], "person", 0.9)
    rider.set_role("rider", moto_id=10)
    assert not rider.violation_no_helmet, "Ban đầu không được có vi phạm"

    # Frame 1: Phát hiện không đội mũ -> chốt vi phạm
    v_engine.process_helmet_result(rider, True, 0.95, dummy_frame)
    assert rider.violation_no_helmet == True, "Phải bật vi phạm không đội mũ"
    assert 15 in v_engine.violating_helmets, "Track 15 phải nằm trong violating_helmets"
    assert 10 in v_engine.violating_helmets, "Moto 10 phải nằm trong violating_helmets"
    assert rider.get_display_label() == "[KO MU] #15", "Label phải là [KO MU]"

    # Frame 2: ViT crop tiếp theo bị mờ/góc nghiêng trả về is_no_helmet = False
    v_engine.process_helmet_result(rider, False, 0.40, dummy_frame)
    assert rider.violation_no_helmet == True, "LATCH: Trạng thái vi phạm không đội mũ KHÔNG ĐƯỢC BỊ TẮT!"
    assert rider.get_display_label() == "[KO MU] #15", "Label vẫn phải giữ vững [KO MU]"

    # Frame 3: Cập nhật vị trí di chuyển qua các frame tiếp theo
    rider.update([200, 220, 250, 340], "person", 0.9)
    # Thử gọi set_role("pedestrian") - không được phép hạ cấp vi phạm
    rider.set_role("pedestrian")
    assert rider.role == "rider", "Không được hạ cấp role của người vi phạm thành pedestrian"
    assert rider.violation_no_helmet == True, "Viền đỏ không mũ phải giữ nguyên vẹn"

    print(">>> TEST HELMET LATCH: TẤT CẢ ĐIỀU KIỆN ĐÃ ĐẠT 100%! VIỀN ĐỎ [KO MU] ĐƯỢC GIỮ VỮNG CHẮC CHẮN!")

if __name__ == "__main__":
    test_helmet_latch()
