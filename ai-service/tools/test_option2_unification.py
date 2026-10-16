import sys
import os
import cv2
import numpy as np

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from core.entity import TrafficEntity
from core.tracker_manager import TrafficTrackerManager
from core.violation_engine import ViolationEngine

class MockBackend:
    def __init__(self):
        self.violations = []
    def send_violation(self, frame, v_type, vehicle_type, conf):
        self.violations.append((v_type, vehicle_type, conf))
    def send_traffic_flow(self, count, vehicle_type):
        pass

def test_option_2():
    print("=" * 65)
    print("--- KIỂM THỬ PHƯƠNG ÁN 2: HỢP NHẤT VI PHẠM MŨ BẢO HIỂM VỀ XE MÁY ---")
    print("=" * 65)

    backend = MockBackend()
    v_engine = ViolationEngine(backend)
    tm = TrafficTrackerManager()
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # -------------------------------------------------------------
    # CASE 1: Xe máy chở 2 người + 1 sub-box trùng lặp phía trước
    # -------------------------------------------------------------
    moto = TrafficEntity(7, [700, 200, 850, 400], "motorcycle", 0.9)
    rider_rear = TrafficEntity(8, [710, 150, 780, 300], "person", 0.88)
    rider_rear.set_role("rider", moto_id=7)
    rider_front = TrafficEntity(20, [750, 160, 820, 310], "person", 0.85)
    rider_front.set_role("rider", moto_id=7)
    subbox_chest = TrafficEntity(24, [740, 210, 800, 320], "person", 0.80)
    subbox_chest.set_role("rider", moto_id=7)
    pedestrian = TrafficEntity(3, [100, 300, 130, 400], "person", 0.9)
    pedestrian.set_role("pedestrian")

    entities = [moto, rider_rear, rider_front, subbox_chest, pedestrian]

    # Giả lập ViT bắt quả tang rider_rear không đội mũ
    v_engine.process_helmet_result(rider_rear, is_no_helmet=True, conf=0.94, clean_frame=dummy_frame)

    # Chạy Phương án 2: Unify & Suppress
    tm.unify_motorcycle_violations(entities, v_engine)

    # 1. Xe máy phải nhận vi phạm và mở rộng box bao trùm cả xe và tất cả người
    assert moto.violation_no_helmet == True, "Xe máy phải được gắn nhãn vi phạm không mũ"
    assert not moto.suppress_render, "Xe máy không được bị ẩn"
    assert moto.get_display_label() == "[KO MU] Xe may #7", f"Nhãn xe máy phải là [KO MU] Xe may #7, thực tế: {moto.get_display_label()}"

    # Box mở rộng: x1 <= 700, y1 <= 150 (đỉnh đầu rider), x2 >= 850, y2 >= 400 (đáy xe)
    rx1, ry1, rx2, ry2 = moto.render_box
    assert rx1 <= 700 and ry1 <= 150 and rx2 >= 850 and ry2 >= 400, f"Box hợp nhất không bao trùm đủ: {moto.render_box}"

    # 2. Toàn bộ các rider con bên trong xe máy phải bị triệt tiêu (suppress_render = True)
    assert rider_rear.suppress_render == True, "Rider ngồi sau phải bị triệt tiêu hiển thị"
    assert rider_front.suppress_render == True, "Rider ngồi trước phải bị triệt tiêu hiển thị"
    assert subbox_chest.suppress_render == True, "Sub-box trùng lặp đùi/ngực phải bị triệt tiêu hiển thị"

    # 3. Người đi bộ trên vỉa hè không bị ảnh hưởng
    assert not pedestrian.suppress_render, "Người đi bộ không được bị ẩn"
    assert pedestrian.get_display_label() == "person #3", "Người đi bộ phải giữ nhãn person"
    assert not pedestrian.violation_no_helmet, "Người đi bộ không bị vi phạm mũ"

    # 4. Khi vẽ lên frame: Đếm số rectangle được vẽ
    render_canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
    for e in entities:
        e.render(render_canvas)

    # Điểm (705, 155) nằm trên viền box hợp nhất của xe máy
    # Kiểm tra màu đỏ vi phạm (0, 0, 255) xuất hiện
    red_pixels = np.sum((render_canvas[:, :, 2] > 200) & (render_canvas[:, :, 0] < 50))
    assert red_pixels > 0, "Khung đỏ vi phạm phải được vẽ lên canvas"

    print("  [DAT] 1. Xe máy chở 2 người + sub-box trùng lặp: Đã gom thành 1 KHUNG ĐỎ DUY NHẤT [KO MU] Xe may #7, triệt tiêu toàn bộ 3 box con.")

    # -------------------------------------------------------------
    # CASE 2: Không có box xe máy (chỉ có 2 rider chồng lấn đè lên nhau)
    # -------------------------------------------------------------
    r1 = TrafficEntity(30, [500, 200, 560, 320], "person", 0.9)
    r1.set_role("rider")
    r2 = TrafficEntity(31, [520, 220, 570, 340], "person", 0.88)
    r2.set_role("rider")
    r1.violation_no_helmet = True
    v_engine.violating_helmets.add(30)

    solo_entities = [r1, r2]
    tm.unify_motorcycle_violations(solo_entities, v_engine)

    assert not r1.suppress_render, "Rider chính không được bị ẩn"
    assert r2.suppress_render == True, "Rider chồng lấn thứ hai phải bị triệt tiêu"
    assert r1.render_box == [500, 200, 570, 340], f"Box rider phải hợp nhất bao trùm cả 2, thực tế: {r1.render_box}"

    print("  [DAT] 2. Hai rider chồng lấn khi không có box xe: Đã gom thành 1 box duy nhất, triệt tiêu box trùng lặp.")
    print("=" * 65)
    print(">>> TẤT CẢ CÁC KIỂM THỬ PHƯƠNG ÁN 2 ĐÃ ĐẠT 100%!")
    print("=" * 65)

if __name__ == "__main__":
    test_option_2()
