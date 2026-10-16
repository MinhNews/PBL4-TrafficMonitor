import time
import cv2
import numpy as np
from collections import Counter
import config

class TrafficEntity:
    """
    Đại diện cho một thực thể giao thông duy nhất được theo dõi qua nhiều frame (Vehicle / Rider / Pedestrian).
    Đóng gói toàn bộ logic:
    - Ổn định nhãn theo thời gian bằng Bỏ phiếu đa số (Majority Voting)
    - Phân định rõ ràng 3 vai trò (role): 'vehicle', 'rider', 'pedestrian'
    - Cố định mép trước (Leading Edge) theo hướng tiếp cận cố định (APPROACH_DIRECTION), không nhảy theo dy
    - Trực quan hóa Bounding Box chuyên nghiệp theo vai trò, không nhấp nháy
    """
    def __init__(self, tracker_id, box, raw_class, conf, stop_line_y=468, approach_direction=None):
        self.id = int(tracker_id)
        self.box = [float(c) for c in box]
        self.raw_class = str(raw_class).lower()
        self.conf = float(conf)
        self.created_at = time.time()
        self.last_updated = self.created_at

        # Hướng xe di chuyển tới vạch dừng (cố định từ config, A1)
        self.approach_direction = approach_direction or getattr(config, "APPROACH_DIRECTION", "up")

        # Lịch sử nhãn nhận diện (20 frame gần nhất) để ổn định lớp
        self.class_history = [self.raw_class]
        self.stable_class = self.raw_class

        # Tọa độ tâm và vận tốc
        cx = (self.box[0] + self.box[2]) / 2.0
        cy = (self.box[1] + self.box[3]) / 2.0
        self.center_history = [(cx, cy)]
        self.velocity_y = 0.0

        # Mép trước xe (Leading Edge): box[1] (đỉnh) nếu xe đi lên, box[3] (đáy) nếu xe đi xuống (A1)
        self.leading_edge_y = self.box[1] if self.approach_direction == "up" else self.box[3]
        self.prev_leading_edge_y = self.leading_edge_y

        # Vai trò giao thông (A3): "vehicle", "rider", "pedestrian"
        if self.stable_class in {"car", "motorcycle", "bus", "truck"}:
            self.role = "vehicle"
        else:
            self.role = "pedestrian"
        self.moto_id = None # ID xe máy tương ứng nếu là rider

        # Trạng thái vi phạm & hiển thị (Phương án 2: Hợp nhất vi phạm)
        self.violation_red_light = False
        self.violation_no_helmet = False
        self.helmet_conf = 0.0
        self.suppress_render = False
        self.render_box = list(self.box)

    @property
    def is_rider(self):
        return self.role == "rider"

    @property
    def is_pedestrian(self):
        return self.role == "pedestrian"

    def set_role(self, role, moto_id=None):
        """Thiết lập vai trò: 'vehicle', 'rider', hoặc 'pedestrian' (A3)"""
        if self.violation_no_helmet and role == "pedestrian":
            return # Đã chốt vi phạm không đội mũ thì bảo lưu vai trò rider
        self.role = role
        if moto_id is not None:
            self.moto_id = moto_id


    def set_rider_status(self, is_rider, moto_id=None):
        """Hàm tương thích ngược với code cũ: gán role thành 'rider' hoặc duy trì"""
        if is_rider:
            self.role = "rider"
            self.moto_id = moto_id
        elif self.stable_class in {"car", "motorcycle", "bus", "truck"}:
            self.role = "vehicle"
        else:
            self.role = "pedestrian"

    def update(self, box, raw_class, conf, stop_line_y=468):
        """Cập nhật tọa độ và trạng thái thực thể trong frame mới"""
        self.box = [float(c) for c in box]
        self.render_box = list(self.box)
        self.suppress_render = False
        self.raw_class = str(raw_class).lower()
        self.conf = float(conf)
        self.last_updated = time.time()

        # 1. Ổn định nhãn lớp bằng BỎ PHIẾU ĐA SỐ (B1)
        self.class_history.append(self.raw_class)
        if len(self.class_history) > 20:
            self.class_history.pop(0)

        counts = Counter(self.class_history)
        # Nếu xe có dấu hiệu rõ ràng của xe hai bánh (motorcycle/bicycle >= 3 lần), ưu tiên nhận diện xe thay vì bị lấn át bởi person
        if (counts.get("motorcycle", 0) >= 3 or counts.get("bicycle", 0) >= 3) and counts.get("person", 0) > max(counts.get("motorcycle", 0), counts.get("bicycle", 0)):
            self.stable_class = "motorcycle" if counts.get("motorcycle", 0) >= counts.get("bicycle", 0) else "bicycle"
        else:
            self.stable_class = counts.most_common(1)[0][0]

        # Cập nhật vai trò vehicle nếu là phương tiện cơ giới
        if self.stable_class in {"car", "motorcycle", "bus", "truck"}:
            self.role = "vehicle"

        # 2. Tính toán Vector vận tốc thực tế (Velocity Δy) phục vụ thống kê
        cx = (self.box[0] + self.box[2]) / 2.0
        cy = (self.box[1] + self.box[3]) / 2.0
        prev_cy = self.center_history[-1][1] if self.center_history else cy
        dy = cy - prev_cy

        if abs(dy) >= 0.2:
            self.velocity_y = dy

        self.center_history.append((cx, cy))
        if len(self.center_history) > 30:
            self.center_history.pop(0)

        # 3. Tính toán mép trước (A1: Cố định theo approach_direction, KHÔNG đổi theo dy)
        self.prev_leading_edge_y = self.leading_edge_y
        self.leading_edge_y = self.box[1] if self.approach_direction == "up" else self.box[3]

    def get_display_label(self):
        """Trả về nhãn hiển thị chính xác theo vai trò giao thông (B3 & Phương án 2)"""
        if self.violation_red_light:
            return f"[VUOT DEN] #{self.id}"
        elif self.violation_no_helmet:
            if self.stable_class in {"motorcycle", "bicycle"}:
                return f"[KO MU] Xe may #{self.id}"
            return f"[KO MU] #{self.id}"
        elif self.role == "rider":
            return f"rider #{self.id}"
        elif self.role == "pedestrian":
            return f"person #{self.id}"
        else:
            return f"{self.stable_class} #{self.id}"

    def render(self, frame):
        """
        Vẽ Bounding Box chuyên nghiệp lên frame (Phương án 2: Bỏ qua các box con bị triệt tiêu):
        - Đỏ rực nếu vi phạm
        - Xám nhạt nếu là người đi bộ (pedestrian)
        - Cyan-Amber thanh lịch cho phương tiện (vehicle) và người lái xe (rider)
        """
        if getattr(self, "suppress_render", False):
            return

        box_to_draw = getattr(self, "render_box", self.box)
        x1, y1, x2, y2 = map(int, box_to_draw)

        if self.violation_red_light or self.violation_no_helmet:
            box_color = (0, 0, 255) # Đỏ rực vi phạm
            text_color = (255, 255, 255)
            font_scale = 0.45
        elif self.role == "pedestrian":
            box_color = (180, 180, 180) # Xám nhạt cho người đi bộ
            text_color = (0, 0, 0)
            font_scale = 0.35
        else:
            box_color = (220, 160, 0) # Cyan-Amber cho vehicle & rider
            text_color = (0, 0, 0)
            font_scale = 0.35

        # Vẽ viền khung
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        # Vẽ badge nhãn có nền màu
        label = self.get_display_label()
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        by = max(th + 4, y1)
        cv2.rectangle(frame, (x1, by - th - 4), (x1 + tw + 6, by + 2), box_color, -1)
        cv2.putText(frame, label, (x1 + 3, by - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 1)


