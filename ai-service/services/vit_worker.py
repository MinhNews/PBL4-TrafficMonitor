import time
import queue
import threading

class AsyncViTWorker:
    """
    Luồng ngầm xử lý phân loại Mũ bảo hiểm Vision Transformer (ViT).
    - Hoạt động bất đồng bộ với hàng đợi (Queue), không làm nghẽn luồng xử lý video chính
    - Điều tiết tần suất phân tích (Throttling 0.12s) để bắt kịp xe di chuyển nhanh
    - Đánh giá chuyển đổi trạng thái [CO MU] và [KO MU] liên tục
    """
    def __init__(self, helmet_clf, violation_engine):
        self.helmet_clf = helmet_clf
        self.violation_engine = violation_engine
        self.queue = queue.Queue(maxsize=25)
        self.track_status = {}         # {tr_id: {"is_no_helmet": bool, "conf": float}}
        self.processing_tracks = set()
        self.last_checked = {}         # {tr_id: timestamp}
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def submit(self, entity, head_crop, clean_frame):
        """Đẩy vùng cắt đầu vào hàng đợi xử lý ngầm"""
        tr_id = entity.id
        now = time.time()
        # Đã chốt vi phạm không đội mũ thì không cần tốn CPU phân tích lại
        if tr_id in self.violation_engine.violating_helmets or (entity.moto_id is not None and entity.moto_id in self.violation_engine.violating_helmets):
            return

        if tr_id in self.processing_tracks or (now - self.last_checked.get(tr_id, 0)) < 0.12:
            return

        if not self.queue.full():
            self.processing_tracks.add(tr_id)
            self.last_checked[tr_id] = now
            self.queue.put_nowait((entity, head_crop.copy(), clean_frame))


    def get_status(self, tr_id):
        """Trả về: (is_no_helmet: bool, conf: float, has_result: bool)"""
        # Nếu đã chốt vi phạm trong violation_engine: Luôn trả về True (Latch vững chắc)
        if tr_id in self.violation_engine.violating_helmets:
            conf = self.track_status.get(tr_id, {}).get("conf", 0.95)
            return True, conf, True
        if tr_id in self.track_status:
            info = self.track_status[tr_id]
            return info["is_no_helmet"], info["conf"], True
        return False, 0.0, False

    def reset(self):
        """Xóa toàn bộ hàng đợi và trạng thái khi video tua lại loop (C2)"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break
        self.track_status.clear()
        self.processing_tracks.clear()
        self.last_checked.clear()
        if hasattr(self.helmet_clf, "reset"):
            self.helmet_clf.reset()
        print("🔄 [VIT WORKER] Đã làm mới toàn bộ hàng đợi và bộ nhớ phân loại mũ.")

    def cleanup_old_tracks(self, active_tr_ids):
        """Dọn dẹp các track đã biến mất quá 5 giây (C3, C4)"""
        now = time.time()
        # Duyệt trên snapshot list() để tránh RuntimeError khi luồng worker ghi vào (C3)
        expired = [tid for tid, ts in list(self.last_checked.items()) if tid not in active_tr_ids and (now - ts) > 5.0]
        for tid in expired:
            self.track_status.pop(tid, None)
            self.last_checked.pop(tid, None)
        # Chỉ xóa lịch sử mũ khi track đã hết hạn 5 giây (C4)
        self.helmet_clf.cleanup_history(expired)

    def _worker(self):
        while self.running:
            try:
                entity, head_crop, clean_frame = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                # Chạy mô hình ViT phân loại mũ bảo hiểm
                confirmed_no_helmet, h_conf = self.helmet_clf.update_and_check(entity.id, head_crop)
                self.track_status[entity.id] = {"is_no_helmet": confirmed_no_helmet, "conf": h_conf}

                # Gửi kết quả sang ViolationEngine để quyết định lập biên bản
                self.violation_engine.process_helmet_result(entity, confirmed_no_helmet, h_conf, clean_frame)
            except Exception as e:
                print(f"[ViT Worker Error] {e}")
            finally:
                if entity.id in self.processing_tracks:
                    self.processing_tracks.remove(entity.id)
                self.queue.task_done()

    def stop(self):
        self.running = False
