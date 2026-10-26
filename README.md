# Frameflow — Video Brief Studio

Ứng dụng web tiếng Việt kết nối **Gemini → ChatGPT**: tải video tham chiếu, phân tích thành creative brief, chỉnh sửa rồi tạo prompt cho Veo, Sora, Runway, Kling, Midjourney hoặc mô hình khác. Có sao chép, xuất Markdown và dữ liệu mẫu minh họa.

## Chạy ứng dụng

Muốn có đường dẫn HTTPS để dùng trên máy/điện thoại của bạn, xem [hướng dẫn triển khai Render](docs/DEPLOY.md). `render.yaml` đã chuẩn bị cấu hình và mật khẩu truy cập; chưa được triển khai lên hosting.

Yêu cầu Python 3.12 trở lên. Không cần cài package hay Node.js.

```sh
cd /workspace/test-phim
cp -n .env.example .env
# Điền khóa của bạn trong .env bằng trình soạn thảo, không commit khóa.
python server.py
```

Mặc định máy chủ lắng nghe tại `127.0.0.1`, cổng `8000`. Dùng trình duyệt trên cùng máy để mở ứng dụng. Cấu hình `HOST`/`PORT` nếu cần; không đưa trực tiếp máy chủ này lên Internet vì chưa có đăng nhập, hạn mức theo người dùng hoặc cơ chế bảo vệ triển khai công khai.

| Biến | Vai trò |
| --- | --- |
| `VIDEO_GEMINI_API_KEY` | Khóa Google AI Studio có quyền dùng Gemini Files và generateContent |
| `VIDEO_OPENAI_API_KEY` | Khóa OpenAI API có hạn mức/thanh toán |
| `GEMINI_MODEL` | Mặc định `gemini-2.5-flash` |
| `OPENAI_MODEL` | Mặc định `gpt-4.1` |
| `HOST` / `PORT` | Mặc định `127.0.0.1` / `8000` |

Cũng dùng được các biến môi trường có sẵn `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`. Biến được tiêm vào môi trường có ưu tiên hơn `.env`. Khởi động lại sau khi đổi cấu hình. ChatGPT Plus không thay thế tài khoản và hạn mức OpenAI API.

## Luồng sử dụng

Giao diện chia thành ba bước: **Video & phân tích → Sơ lược & viết lại → Prompt hoàn chỉnh**. Bấm các bước để chuyển qua lại mà không mất nội dung đang nhập; sau khi xử lý thành công ứng dụng tự mở bước tiếp theo. Có thể dùng phím mũi tên khi thanh bước đang được chọn. Nút trạng thái API mở thông tin cấu hình riêng cho Gemini và OpenAI. Hai ô hướng dẫn đều có nút khôi phục mẫu; ứng dụng hỏi trước khi thay nội dung đã chỉnh.

1. Chọn MP4, MOV, WebM hoặc MPEG, tối đa 100 MB. Bản này hỗ trợ **tệp tải lên**, chưa hỗ trợ dán link TikTok/YouTube.
2. Chọn phân tích: máy chủ dùng Gemini Files API (resumable upload), chờ video xử lý rồi yêu cầu tóm tắt, hook, phân cảnh, âm thanh, màu sắc và CTA bằng tiếng Việt.
3. Kiểm tra và sửa bản sơ lược; thêm sản phẩm/khán giả/phong cách cho ý tưởng mới. Có thể dán brief có sẵn để bỏ qua Gemini.
4. Chọn mô hình đích và ngôn ngữ. ChatGPT qua OpenAI Responses API tạo concept, master prompt, prompt từng cảnh và ghi chú sản xuất.
5. Sao chép hoặc tải `.md`. Đây là công cụ tạo **prompt**, không render video và không gọi API của mô hình đích.

Hai ô hướng dẫn độc lập cho phép tùy chỉnh từng bước:

- **Hướng dẫn Gemini:** quy trình phân tích video, ví dụ tập trung vào hook, chép lời thoại, lập bảng phân cảnh hoặc phân tích âm thanh. Gửi kèm video chỉ tới Gemini. Sửa ô này rồi bấm phân tích lại để áp dụng; bản sơ lược hiện tại không tự thay đổi.
- **Hướng dẫn ChatGPT:** yêu cầu viết lại bản sơ lược, ví dụ chỉ xuất một prompt hoàn chỉnh, chia cảnh 5 giây hoặc đổi phong cách kể chuyện. Gửi tới OpenAI cùng bản sơ lược, định hướng, mô hình đích và ngôn ngữ.

Mỗi ô hướng dẫn Gemini và ChatGPT tối đa 80.000 ký tự, có nội dung gợi ý sửa được; để trống sẽ dùng hướng dẫn mặc định. Bản sơ lược tối đa 60.000 ký tự, định hướng ý tưởng tối đa 10.000 ký tự. Hướng dẫn không được lưu sau khi tải lại trang. Không điền khóa API vào các ô nội dung.

Nút “Thử với dữ liệu mẫu” dùng nội dung cố định, không gọi API. Nút tạo prompt vẫn gọi ChatGPT thật, kể cả khi đang dùng bản sơ lược mẫu. Trạng thái API trên giao diện chỉ biểu thị đã có khóa, không xác nhận khóa hợp lệ.

## Dữ liệu và giới hạn

- Khóa chỉ được đọc ở máy chủ; không lưu vào trình duyệt hoặc trả về từ API trạng thái.
- Video đi đến Google, brief và định hướng đi đến OpenAI. Chỉ gửi nội dung bạn có quyền xử lý; tham khảo chính sách dữ liệu của từng nhà cung cấp.
- Không lưu video hoặc kết quả vào ổ đĩa ứng dụng. Video nằm tạm trong RAM, tối đa 100 MB mỗi yêu cầu. Đóng tab làm mất kết quả chưa xuất.
- Máy chủ yêu cầu xóa tệp Gemini trong bước dọn dẹp sau phân tích. Nếu dọn dẹp thất bại hoặc tiến trình dừng đột ngột, Gemini Files tự hết hạn sau 48 giờ.
- OpenAI dùng `store: false`; điều này không thay thế chính sách lưu giữ dữ liệu của nhà cung cấp.
- Video dài có thể chậm và tốn phí. Không có tự động gửi lại để tránh phát sinh phí trùng. Nếu kết nối bị gián đoạn, kiểm tra bảng sử dụng API trước khi thử lại.
- Thiết kế dành cho một người dùng trong môi trường phát triển. Trước khi triển khai công khai cần bổ sung xác thực, quản lý khóa theo người dùng, giới hạn đồng thời/kích thước ở proxy, hàng đợi tác vụ và HTTPS.

## Kiểm thử

```sh
cd /workspace/test-phim
python -m unittest -v
node --check static/app.js  # Tùy chọn nếu có Node
```

Kiểm thử HTTP với phản hồi nhà cung cấp giả lập bao phủ tải lên/chờ/xóa tệp Gemini, tạo prompt OpenAI, lỗi khóa, đầu vào, nguồn yêu cầu và che nội dung lỗi. **Không phải kiểm thử API thật.** Để xác minh đầu cuối: cấu hình hai khóa, tải video ngắn hợp lệ, phân tích rồi tạo prompt và xác nhận kết quả trong giao diện.

Kết nối HTTPS cần cho phép `generativelanguage.googleapis.com` và `api.openai.com`. Kiểm tra sẵn sàng nội bộ bằng `GET /api/status` và tải trang `/`; không cần khóa để mở giao diện hoặc xem mẫu.
