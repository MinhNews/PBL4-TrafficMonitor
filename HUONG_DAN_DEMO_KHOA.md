# 🚦 HƯỚNG DẪN CHUẨN BỊ MÔI TRƯỜNG & KỊCH BẢN DEMO BÁO CÁO TUẦN 7
> **Dành riêng cho:** Leader Phan Quang Đăng Khoa  
> **Dự án:** PBL4 - Hệ thống Giám sát & Xử lý Vi phạm Giao thông Thông minh (Nhóm 3)  
> *(Ghi chú: Bo mạch thật ESP32 Khoa đã lắp và nạp code xong, tài liệu này chỉ tập trung vào cài đặt trên Laptop và kịch bản thuyết trình demo).*

---

## MỤC LỤC
1. [Yêu cầu phần mềm cần có trên máy tính](#1-yêu-cầu-phần-mềm-cần-có-trên-máy-tính)
2. [Cài đặt dự án lần đầu trên máy Khoa (Làm 1 lần)](#2-cài-đặt-dự-án-lần-đầu-trên-máy-khoa-làm-1-lần)
3. [Thứ tự khởi động hệ thống khi demo](#3-thứ-tự-khởi-động-hệ-thống-khi-demo)
4. [Kịch bản thuyết trình & Thao tác demo (Từng bước chi tiết)](#4-kịch-bản-thuyết-trình--thao-tác-demo-từng-bước-chi-tiết)
5. [Mẹo xử lý tình huống khẩn cấp (Troubleshooting)](#5-mẹo-xử-lý-tình-huống-khẩn-cấp-troubleshooting)

---

## 1. YÊU CẦU PHẦN MỀM CẦN CÓ TRÊN MÁY TÍNH

Trước buổi demo, Khoa kiểm tra xem máy tính của mình đã cài đủ các công cụ sau chưa:

| Công cụ | Phiên bản khuyến nghị | Mục đích | Kiểm tra bằng lệnh |
| :--- | :--- | :--- | :--- |
| **Git** | Mới nhất | Kéo mã nguồn từ GitHub | `git --version` |
| **Node.js** | v18.x hoặc v20.x LTS | Chạy giao diện Web Frontend React (Vite) | `node -v` |
| **Java JDK** | JDK 17 hoặc 21 | Chạy Backend Spring Boot | `java -version` |
| **Maven** | 3.8+ (hoặc có sẵn trong IntelliJ) | Biên dịch Backend Java | `mvn -v` |
| **MySQL Server** | 8.0+ (hoặc XAMPP MySQL) | Cơ sở dữ liệu lưu biên bản & thống kê | Mở XAMPP / MySQL Workbench |
| **Python** | 3.10 hoặc 3.11 (64-bit) | Chạy AI Service (YOLOv8 + ByteTrack) | `python --version` |

---

## 2. CÀI ĐẶT DỰ ÁN LẦN ĐẦU TRÊN MÁY KHOA (LÀM 1 LẦN)

### Bước 2.1: Kéo code mới nhất từ nhánh `main`
Mở Terminal / PowerShell tại thư mục làm việc của Khoa:
```powershell
git clone https://github.com/MinhNews/PBL4-TrafficMonitor.git
cd PBL4-TrafficMonitor
git checkout main
git pull origin main
```

---

### Bước 2.2: Cấu hình Cơ sở dữ liệu MySQL & Backend
1. **Khởi động MySQL:** Bật XAMPP (Start module MySQL) hoặc bật MySQL Service.
2. **Khởi tạo dữ liệu:**
   - Mở MySQL Workbench, Navicat hoặc phpMyAdmin (`http://localhost/phpmyadmin`).
   - Mở và chạy toàn bộ nội dung file: `backend/src/main/resources/schema.sql`.
   - *(File này tự động tạo Database `traffic_db`, các bảng và tài khoản Admin: `admin` / `admin123`)*.
3. **Tạo file cấu hình Backend:**
   - Vào thư mục `backend/src/main/resources/`.
   - Copy file `application.properties.example` và đổi tên thành `application.properties`.
   - Mở file `application.properties`, sửa **dòng 7** thành mật khẩu root MySQL trên máy Khoa:
     ```properties
     spring.datasource.password=mat_khau_mysql_cua_khoa
     ```
     *(Nếu dùng XAMPP mặc định không có mật khẩu thì để trống: `spring.datasource.password=`)*.

---

### Bước 2.3: Cài đặt Frontend (React + Vite)
Mở Terminal mới tại thư mục `frontend`:
```powershell
cd PBL4-TrafficMonitor/frontend
npm install
```

---

### Bước 2.4: Cài đặt môi trường AI Python
Mở Terminal mới tại thư mục `ai-service`:
```powershell
cd PBL4-TrafficMonitor/ai-service

# 1. Tạo môi trường ảo riêng biệt
python -m venv pbl4_env

# 2. Kích hoạt môi trường ảo
.\pbl4_env\Scripts\Activate.ps1
# (Nếu PowerShell chặn script, chạy lệnh: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass rồi kích hoạt lại)

# 3. Cài đặt toàn bộ thư viện cần thiết
pip install -r requirements.txt
```
> [!NOTE]
> File trọng số AI `yolo11n.pt` đã tích hợp sẵn trong repo. Đối với video demo `traffic2.mp4`, Minh gửi qua Zalo/Drive, Khoa chỉ cần copy vào thư mục `ai-service/dataset/traffic2.mp4` (hoặc để ngoài Desktop rồi chạy với cờ `--source "đường_dẫn_video"`).

---

## 3. THỨ TỰ KHỞI ĐỘNG HỆ THỐNG KHI DEMO

Khi chuẩn bị lên thuyết trình trước thầy cô, mở **3 cửa sổ Terminal riêng biệt** theo đúng thứ tự sau:

### 🟢 Terminal 1: Khởi động Backend (Cổng 8080)
```powershell
cd PBL4-TrafficMonitor/backend
mvn spring-boot:run
```
*(Chờ khoảng 5-10 giây đến khi thấy dòng chữ: `Started TrafficmonitorApplication in ... seconds`)*.

---

### 🟢 Terminal 2: Khởi động AI Service (Cổng 5000)
```powershell
cd PBL4-TrafficMonitor/ai-service
.\pbl4_env\Scripts\python.exe detectors/test_detector.py --no-gui
```
*(Chờ thấy dòng chữ: `Server phát luồng Web mở tại: http://localhost:5000/video_feed`)*.

---

### 🟢 Terminal 3: Khởi động Web Frontend (Cổng 5173)
```powershell
cd PBL4-TrafficMonitor/frontend
npm run dev
```
*(Mở trình duyệt Google Chrome truy cập vào: **`http://localhost:5173`**)*.

---

### 🟢 Bật nguồn bo mạch thật ESP32
- Cắm nguồn bo ESP32 (qua cáp USB laptop hoặc sạc dự phòng).
- Đảm bảo ESP32 đã kết nối vào mạng WiFi (khuyên dùng **Hotspot 2.4GHz từ điện thoại** để tránh tường lửa mạng trường).
- Màn hình OLED trên bo sáng chữ `PBL4 - TRAFFIC IOT` và bắt đầu đếm giây đèn đỏ/xanh/vàng.

---

## 4. KỊCH BẢN THUYẾT TRÌNH & THAO TÁC DEMO (TỪNG BƯỚC CHI TIẾT)

Khoa có thể trình bày theo 5 màn kịch bản chuẩn mực dưới đây:

### Màn 1: Đăng nhập & Tổng quan kiến trúc
* **Thao tác:** Mở trình duyệt tại `http://localhost:5173`.
* **Thao tác:** Đăng nhập tài khoản: `admin` | Mật khẩu: `admin123`.
* **Khoa thuyết minh:**
  > *"Kính thưa thầy cô, hệ thống của nhóm được xây dựng theo mô hình vòng lặp khép kín giữa Phần cứng IoT, Thị giác máy tính AI, Backend Spring Boot và Web Dashboard. Hệ thống bảo mật đăng nhập với cơ chế JWT và mật khẩu mã hóa BCrypt một chiều."*

---

### Màn 2: Chứng minh đồng bộ Phần cứng IoT thời gian thực
* **Thao tác:** Vào mục **Dashboard**. Chỉ con trỏ chuột vào cột đèn 3 bóng (🔴 Đỏ, 🟡 Vàng, 🟢 Xanh) bên cạnh khung video trực tiếp.
* **Khoa chỉ tay vào bo ESP32 đang đặt trên bàn:**
  > *"Tại ngã tư, bo ESP32 thực tế đang điều khiển 3 đèn LED tín hiệu và màn hình OLED đếm ngược. Nhờ kết nối giao thức MQTT Cloud Broker qua topic `pbl4/nhom3/traffic/light`, toàn bộ trạng thái màu đèn và từng giây đếm ngược trên Web đang khớp 100% với bo mạch thật ngoài đời mà thầy cô đang nhìn thấy trên bàn."*
* **Khoa chỉ vào nhãn xanh:**
  > *"Hệ thống tự động phát hiện Heartbeat từ bo mạch với thẻ trạng thái `● ESP32 Online`. Khi có bo mạch thật hoạt động, hệ thống tự động khóa toàn bộ các nút can thiệp thủ công trên Web để đảm bảo an toàn tuyệt đối và tính khách quan ngoài hiện trường."*

---

### Màn 3: Bắt quả tang xe vượt đèn đỏ & Kích hoạt Còi hú hiện trường
* **Thao tác:** Chờ chu kỳ đèn trên ESP32 chuyển sang **ĐÈN ĐỎ**:
  - Trên màn hình video: Vạch dừng tức thì chuyển sang **MÀU ĐỎ RỰC** (`VACH DUNG - DEN DO`).
  - Khi một xe ô tô hoặc xe máy trong video di chuyển vượt qua vạch dừng:
* **Hiện tượng xảy ra đồng thời:**
  1. **Trên Video:** Hộp nhận diện của xe đó bị khóa sang màu đỏ vi phạm vĩnh viễn kèm nhãn cảnh báo.
  2. **Trên Web Frontend:**
     - Âm thanh chuông báo động trên Web vang lên.
     - Góc phải màn hình nảy **Toast cảnh báo màu đỏ**.
     - Thẻ KPI `Tổng vi phạm hôm nay` và `Vượt đèn đỏ` tự động nhảy số tức thì qua WebSocket STOMP (không cần F5 lại trang).
     - Bảng `Danh sách vi phạm gần đây` xuất hiện ngay biên bản mới với ảnh chụp cắt vi phạm rõ nét.
  3. **Trên bo mạch ESP32 của Khoa đặt trên bàn:**
     - Còi Active Buzzer lập tức **hú vang 4 tiếng BÍP BÍP dồn dập**.
     - Đèn LED đỏ chớp tắt liên tục.
     - Màn hình OLED SSD1306 chuyển sang màn hình cảnh báo khẩn cấp: `!CANH BAO! PHAT HIEN VI PHAM`.
* **Khoa thuyết minh:**
  > *"Khi AI phát hiện vi phạm lúc đèn đỏ, nó gửi dữ liệu ngầm lên Backend Spring Boot. Backend lập tức đẩy thông báo thời gian thực lên Dashboard qua WebSocket STOMP, đồng thời xuất bản tin MQTT xuống bo ESP32 để kích hoạt còi hú và màn hình OLED cảnh báo trực tiếp tại hiện trường."*

---

### Màn 4: Nghiệp vụ xử lý biên bản & Nghị định 168/2024/NĐ-CP
* **Thao tác:** Bấm vào biểu tượng **Con mắt** (Xem chi tiết) tại dòng vi phạm vừa bắt được.
* **Khoa chỉ vào Modal chi tiết:**
  > *"Đây là hồ sơ biên bản điện tử hoàn chỉnh. Bằng chứng hình ảnh được Backend tự động lưu trữ trên Cloudinary với độ phân giải cao. Hệ thống tự động tra cứu và áp dụng mức phạt tiền cùng quy định trừ điểm giấy phép lái xe theo đúng Nghị định 168/2024/NĐ-CP mới nhất: ví dụ ô tô vượt đèn đỏ phạt 5.000.000đ, xe máy phạt 900.000đ."*
* **Thao tác:** Bấm nút **"Xác nhận xử phạt"** để chuyển trạng thái biên bản sang `Đã xử lý`.

---

### Màn 5: Thống kê lưu lượng phương tiện & Kết luận
* **Thao tác:** Cuộn xuống phần biểu đồ **Lưu lượng theo giờ (Hourly Traffic Flow)**.
* **Khoa thuyết minh:**
  > *"Bên cạnh xử phạt vi phạm, mô hình AI còn liên tục đếm số lượng phương tiện lưu thông qua nút giao và gửi về Backend để vẽ biểu đồ lưu lượng theo từng khung giờ trong ngày, giúp lực lượng chức năng có cái nhìn tổng quan để điều tiết giao thông thông minh. Nhóm đã hoàn thành xuất sắc toàn bộ các luồng yêu cầu của Đồ án PBL4."*

---

## 5. MẸO XỬ LÝ TÌNH HUỐNG KHẨN CẤP (TROUBLESHOOTING)

| Hiện tượng | Nguyên nhân | Cách xử lý nhanh |
| :--- | :--- | :--- |
| **Backend báo lỗi: `Access denied for user 'root'`** | Sai mật khẩu MySQL trong `application.properties` | Mở `backend/src/main/resources/application.properties`, kiểm tra lại dòng `spring.datasource.password=` xem đã đúng mật khẩu MySQL máy Khoa chưa. |
| **Web hiện `○ Giả lập` thay vì `● ESP32 Online`** | ESP32 chưa kết nối được WiFi hoặc MQTT | 1. Bật Hotspot 2.4GHz trên điện thoại, kiểm tra ESP32 đã nối vào chưa.<br>2. Cắm cáp mở Serial Monitor (Baud 115200) xem ESP32 đã in `MQTT Connected` chưa. |
| **Terminal báo `Address already in use: bind` (Cổng 8080/5000)** | Có tiến trình chạy ngầm từ trước đang chiếm cổng | Mở PowerShell gõ:<br>`Get-Process java, python -ErrorAction SilentlyContinue \| Stop-Process -Force` rồi chạy lại. |
| **AI báo lỗi thiếu thư viện Python** | Quên kích hoạt môi trường ảo `pbl4_env` | Đảm bảo dòng lệnh có kích hoạt `pbl4_env` trước khi chạy:<br>`cd ai-service`<br>`.\pbl4_env\Scripts\python.exe detectors/test_detector.py --no-gui` |

---
*Chúc Khoa và Nhóm 3 có một buổi báo cáo Demo Tuần 7 thật tự tin và đạt kết quả cao nhất!* 🚀
