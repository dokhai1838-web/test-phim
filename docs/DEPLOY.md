# Đưa Frameflow lên Render

File `render.yaml` chuẩn bị một web service Python với HTTPS do Render quản lý, mật khẩu truy cập và health check. Chưa có dịch vụ nào được tạo chỉ bằng việc thêm file này.

## 1. Đưa mã nguồn lên GitHub

Mã nguồn hiện nằm trong môi trường Codex; nếu GitHub vẫn trống thì Render chưa thể lấy mã để triển khai. Đẩy các file dự án lên nhánh `main` của `dokhai1838-web/test-phim` qua thao tác Git được cấp quyền. Không đưa `.env`, khóa API hoặc mật khẩu vào Git. `.gitignore` đã bỏ qua `.env`.

## 2. Kết nối Render

1. Truy cập https://dashboard.render.com và đăng nhập.
2. Chọn **New → Blueprint**, kết nối GitHub và chọn repository `dokhai1838-web/test-phim`, nhánh `main`.
3. Render đọc `render.yaml`. Kiểm tra service `frameflow-studio`, cấu hình và gói dịch vụ trước khi tạo. Blueprint đề xuất gói Free; khả năng cung cấp và giới hạn phụ thuộc tài khoản/Render ở thời điểm triển khai.
4. Triển khai. Build chạy 15+ kiểm thử; sau khi thành công, Render cấp URL HTTPS trong trang service. Không đoán URL từ tên dịch vụ vì tên có thể bị trùng.

## 3. Mở giao diện

Trong mục **Environment** của service, xem mật khẩu `APP_PASSWORD` do Render tạo, giữ riêng tư. Mở URL HTTPS thật của service, đăng nhập hộp thoại trình duyệt với tên `admin` và mật khẩu đó. Có thể xem mẫu ngay mà chưa cần khóa AI. Không gửi mật khẩu trong chat.

## 4. Kết nối AI

Thêm hai biến trong **Environment** trên Render, lưu và khởi động/triển khai lại:

- `VIDEO_GEMINI_API_KEY`: khóa Gemini API.
- `VIDEO_OPENAI_API_KEY`: khóa OpenAI API.

Cài đặt trong môi trường Codex không tự chuyển sang Render. ChatGPT Plus không thay thế hạn mức OpenAI API. Không đặt khóa vào mã nguồn, hướng dẫn hay trường không được bảo mật.

## 5. Xác minh

- `/healthz` trả `{"status":"ok"}` công khai, không chứa thông tin cấu hình. Nó không xác minh API AI.
- Trang chủ và API ứng dụng yêu cầu đăng nhập khi có `APP_PASSWORD`.
- Thử mẫu, đổi bước, tải Markdown. Sau khi có khóa, dùng một video ngắn có quyền xử lý để thử phân tích và tạo prompt thật.

## Phạm vi triển khai

Đây là bản dùng thử riêng cho một người hoặc nhóm nhỏ dùng chung mật khẩu, chưa có tài khoản riêng, hạn mức theo người dùng hay hàng đợi lưu bền. Máy chủ chỉ xử lý một yêu cầu AI/tải lên đồng thời; yêu cầu tiếp theo nhận thông báo bận. Gói miễn phí có thể ngủ khi không dùng, mất thời gian khởi động và gặp giới hạn RAM/thời gian chờ với video dài. Bắt đầu với video ngắn, dung lượng nhỏ. Tệp tải lên vẫn giới hạn 100 MB; giới hạn proxy của hosting cũng có thể áp dụng. Chưa xác minh triển khai Render thực tế, phiên bản Python có sẵn, hoặc xử lý video thật trên gói này. Đổi sang tác vụ nền/hàng đợi trước khi phục vụ nhiều người hoặc video dài.
