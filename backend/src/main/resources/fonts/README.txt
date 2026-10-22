Font dùng để sinh biên bản PDF (C3)
====================================

Roboto-Regular.ttf
Roboto-Bold.ttf
    Nguồn: https://github.com/googlefonts/roboto (thư mục src/hinted)
    Giấy phép: Apache License 2.0
    Lý do chọn: hỗ trợ đầy đủ dấu tiếng Việt, dung lượng nhỏ (~500 KB/tệp),
    nhúng trực tiếp vào PDF nên file xuất ra hiển thị đúng dấu trên mọi máy
    (không phụ thuộc font cài sẵn của hệ điều hành).

Các tệp này được ViolationPdfService nạp từ classpath:
    /fonts/Roboto-Regular.ttf
    /fonts/Roboto-Bold.ttf
Nếu xoá, PDF vẫn tạo được nhưng sẽ tự lùi về font Helvetica (mất dấu tiếng Việt)
và ghi cảnh báo vào log backend.
