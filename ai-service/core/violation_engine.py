import time
import cv2
import config

class ViolationEngine:
    """
    Động cơ phân tích và bắt lỗi vi phạm giao thông (Violation Engine).
    Đóng gói toàn bộ quy tắc nghiệp vụ:
    - Bắt lỗi Vượt đèn đỏ theo mép đầu xe (Leading Edge) tức thời, loại trừ người đi bộ và người ngồi trên xe (A1, A2)
    - Chỉ các phương tiện cơ giới {car, motorcycle, bus, truck} mới được đếm lưu lượng và bắt vượt đèn đỏ (A2)
    - Cơ chế Kế thừa vi phạm chặt chẽ (IoU > 0.5, cùng lớp, tuổi 0.2-3.0s) khi ByteTrack nhảy ID (A4)
    - Bộ đếm vi phạm độc lập violation_count tăng đúng 1 lần mỗi biên bản gửi đi (A5)
    - Khóa báo lặp Cooldown 30s cho mỗi phương tiện
    """
    VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}

    def __init__(self, backend_service):
        self.backend = backend_service
        self.violating_vehicles = {} # {tracker_id: {"timestamp": float, "box": list, "cls": str}}
        self.violating_helmets = set() # {tracker_id} - Chốt trạng thái vi phạm không đội mũ (Latch)
        self.passed_vehicles = set() # ID các xe đã đếm qua vạch
        self.reported_violations = {} # {entity_key: timestamp} - Cooldown chống báo lặp
        self.violation_count = 0 # A5: Bộ đếm vi phạm độc lập, chuẩn xác cho /status
        self.approach_direction = getattr(config, "APPROACH_DIRECTION", "up")

    def reset(self):
        """Làm mới toàn bộ bộ nhớ vi phạm khi tua lại video loop hoặc đổi camera"""
        self.violating_vehicles.clear()
        self.violating_helmets.clear()
        self.passed_vehicles.clear()
        self.reported_violations.clear()
        self.violation_count = 0
        print("🔄 [VIOLATION ENGINE] Đã làm mới toàn bộ danh sách vi phạm & lưu lượng xe.")


    @staticmethod
    def _box_iou(boxA, boxB):
        """Tính độ trùng lặp IoU giữa 2 bounding box"""
        if boxA is None or boxB is None or len(boxA) < 4 or len(boxB) < 4:
            return 0.0
        xa = max(boxA[0], boxB[0])
        ya = max(boxA[1], boxB[1])
        xb = min(boxA[2], boxB[2])
        yb = min(boxA[3], boxB[3])
        inter = max(0.0, xb - xa) * max(0.0, yb - ya)
        areaA = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        areaB = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
        union = areaA + areaB - inter
        return inter / max(1.0, union)

    @staticmethod
    def check_line_crossing(prev_y, curr_y, stop_line_y, approach_direction="up"):
        """
        Kiểm tra mép đầu xe cắt qua vạch ngã tư THEO ĐÚNG 1 CHIỀU CẤU HÌNH (A1):
        - Chiều đi lên (Y giảm dần): prev_y >= stop_line_y và curr_y < stop_line_y
        - Chiều đi xuống (Y tăng dần): prev_y <= stop_line_y và curr_y > stop_line_y
        Xe ngược chiều hoặc đứng rung lắc tại vạch tuyệt đối không bị tính.
        """
        if prev_y is None or curr_y is None:
            return False
        if approach_direction == "up":
            return (prev_y >= stop_line_y and curr_y < stop_line_y)
        else:
            return (prev_y <= stop_line_y and curr_y > stop_line_y)

    def check_traffic_flow(self, entity, stop_line_y):
        """
        Đếm lưu lượng phương tiện cơ giới thực tế:
        Áp dụng cho xe cơ giới (vehicle) hoặc người điều khiển xe trên đường (rider).
        Người đi bộ (pedestrian) tuyệt đối bị loại trừ.
        """
        if entity.role == "pedestrian":
            return False

        if entity.stable_class not in self.VEHICLE_CLASSES and entity.role != "rider":
            return False

        if entity.id in self.passed_vehicles:
            return False

        crossed = self.check_line_crossing(
            entity.prev_leading_edge_y, entity.leading_edge_y, stop_line_y, self.approach_direction
        )
        if crossed:
            self.passed_vehicles.add(entity.id)
            veh_type = "car" if entity.stable_class in ["car", "bus", "truck"] else "motorcycle"
            self.backend.send_traffic_flow(count=1, vehicle_type=veh_type)
            print(f"📊 [LƯU LƯỢNG XE] Xe #{entity.id} ({veh_type.upper()}) qua ngã tư. Tổng: {len(self.passed_vehicles)}")
            return True
        return False

    def check_red_light_violation(self, entity, current_light, stop_line_y, clean_frame):
        """
        Kiểm tra xe cơ giới vượt đèn đỏ theo mép đầu xe (A1, A2).
        Áp dụng cho xe cơ giới (vehicle) hoặc người điều khiển xe máy trên đường (rider).
        Người đi bộ (pedestrian) tuyệt đối không bị phạt.
        """
        if entity.role == "pedestrian":
            return False

        if entity.stable_class not in self.VEHICLE_CLASSES and entity.role != "rider":
            return False

        now = time.time()

        # 1. Nếu xe này đã vi phạm: Tiếp tục duy trì trạng thái vi phạm (chống mất khung đỏ)
        if entity.id in self.violating_vehicles:
            self.violating_vehicles[entity.id]["timestamp"] = now
            self.violating_vehicles[entity.id]["box"] = entity.box
            entity.violation_red_light = True
            return True

        # 2. Cơ chế Kế thừa vi phạm chặt chẽ (A4):
        for v_id, v_data in list(self.violating_vehicles.items()):
            age = now - v_data["timestamp"]
            if 0.2 <= age <= 3.0 and v_data.get("cls") == entity.stable_class:
                if self._box_iou(entity.box, v_data["box"]) > 0.5:
                    self.violating_vehicles[entity.id] = {
                        "timestamp": now,
                        "box": entity.box,
                        "cls": entity.stable_class
                    }
                    entity.violation_red_light = True
                    return True # Kế thừa chỉ để hiển thị, KHÔNG tăng violation_count

        # 3. Kiểm tra mép đầu xe cắt qua vạch dừng đúng 1 chiều khi đèn ĐỎ (A1)
        crossed = self.check_line_crossing(
            entity.prev_leading_edge_y, entity.leading_edge_y, stop_line_y, self.approach_direction
        )

        if crossed and current_light == "RED":
            self.violating_vehicles[entity.id] = {
                "timestamp": now,
                "box": entity.box,
                "cls": entity.stable_class
            }
            self.reported_violations[entity.id] = now
            self.violation_count += 1 # A5: Tăng đúng 1 lần cho biên bản thật
            entity.violation_red_light = True

            veh_type = "CAR" if entity.stable_class in ["car", "bus", "truck"] else "MOTORCYCLE"
            print(f"\n🚨 [AI PHÁT HIỆN VI PHẠM #{self.violation_count}] Xe #{entity.id} ({veh_type}) VƯỢT ĐÈN ĐỎ tại vạch Y={stop_line_y}!")

            # Tạo ảnh bằng chứng sạch chỉ khoanh khung đỏ quanh xe vi phạm
            evidence = clean_frame.copy()
            bx1, by1, bx2, by2 = map(int, entity.box)
            cv2.rectangle(evidence, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
            cv2.putText(evidence, f"VUOT DEN DO #{entity.id}", (bx1, max(20, by1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            self.backend.send_violation(evidence, "RED_LIGHT_CROSS", veh_type, entity.conf)
            return True

        return False

    def process_helmet_result(self, entity, is_no_helmet, conf, clean_frame):
        """
        Cập nhật kết quả phân loại Mũ bảo hiểm từ ViT Worker.
        Chỉ phạt người điều khiển xe máy (role == 'rider'), gom biên bản theo mã xe máy (moto_id).
        Duy trì chốt vi phạm (Latch) để viền đỏ [KO MU] không bị tắt khi xe di chuyển.
        """
        # Nếu xe/người này đã từng bị chốt vi phạm không đội mũ: DUY TRÌ KHÓA VI PHẠM (Latch)
        if entity.id in self.violating_helmets or (entity.moto_id is not None and entity.moto_id in self.violating_helmets):
            entity.violation_no_helmet = True
            entity.set_role("rider", moto_id=entity.moto_id)
            return

        if entity.role == "pedestrian" and not is_no_helmet:
            return

        if is_no_helmet:
            # Chốt trạng thái vi phạm vĩnh viễn cho track này (Latch)
            self.violating_helmets.add(entity.id)
            if entity.moto_id is not None:
                self.violating_helmets.add(entity.moto_id)

            entity.violation_no_helmet = True
            entity.helmet_conf = conf
            entity.set_role("rider", moto_id=entity.moto_id)

            now = time.time()
            entity_key = f"moto_{entity.moto_id}" if entity.moto_id is not None else f"rider_{entity.id}"
            last_sent = self.reported_violations.get(entity_key, 0)

            # Khóa chống gửi trùng lặp: Mỗi xe tối đa 1 biên bản trong 30 giây
            if (now - last_sent) > 30.0:
                self.reported_violations[entity_key] = now
                self.violation_count += 1 # A5: Tăng đúng 1 lần
                target_label = f"Xe máy #{entity.moto_id}" if entity.moto_id is not None else f"Rider #{entity.id}"
                print(f"🚨 [AI PHÁT HIỆN VI PHẠM #{self.violation_count}] {target_label} KHÔNG ĐỘI MŨ BẢO HIỂM! (Độ tin cậy: {int(conf * 100)}%)")

                evidence = clean_frame.copy()
                bx1, by1, bx2, by2 = map(int, entity.box)
                cv2.rectangle(evidence, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
                cv2.putText(evidence, f"KHONG DOI MU {int(conf * 100)}%", (bx1, max(20, by1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                self.backend.send_violation(evidence, "NO_HELMET", "MOTORCYCLE", conf)
        else:
            entity.violation_no_helmet = False
            entity.helmet_conf = conf


