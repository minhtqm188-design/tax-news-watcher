# Theo dõi tin tức sắc thuế Việt Nam

Tự động tìm tin tức mới về các sắc thuế (TNCN, VAT, TNDN, tiêu thụ đặc biệt, xuất nhập khẩu, bảo vệ môi trường, sử dụng đất, tài nguyên, lệ phí trước bạ, thuế nhà thầu, hộ kinh doanh, chuyển nhượng bất động sản...) qua Google News RSS, lưu lại vào `data/tax_news.json` và gửi thông báo qua [ntfy](https://ntfy.sh) khi có tin mới.

## Cách hoạt động

- `scripts/check_tax_news.py` truy vấn Google News RSS cho từng từ khóa trong `KEYWORDS`.
- So sánh với các bài đã ghi nhận (`data/tax_news.json`) để chỉ lấy tin mới, trong vòng `MAX_AGE_DAYS` ngày gần nhất (mặc định 10 ngày).
- Ghi tin mới vào `data/tax_news.json` và gửi 1 thông báo ntfy tổng hợp.
- Chạy tự động mỗi thứ Hai (7h sáng giờ VN) qua GitHub Actions (`.github/workflows/tax-news-check.yml`), hoặc chạy tay bằng nút "Run workflow" trên tab Actions.

## Thiết lập lần đầu

1. **Tạo topic ntfy riêng** (không cần đăng ký tài khoản):
   - Nghĩ ra một tên topic khó đoán, ví dụ `vn-thue-updates-<vài ký tự ngẫu nhiên>`.
   - Cài app [ntfy](https://ntfy.sh/app) trên điện thoại (Android/iOS) hoặc dùng web `https://ntfy.sh/<tên-topic>`, subscribe vào topic bạn vừa nghĩ ra.
   - Lưu ý: ai biết tên topic cũng đọc được thông báo, nên chọn tên đủ khó đoán và không chia sẻ công khai.

2. **Đẩy code này lên một repo GitHub** (chưa có git repo, cần khởi tạo):
   ```bash
   git init
   git add .
   git commit -m "init: tax news watcher"
   git branch -M main
   git remote add origin <URL repo GitHub của bạn>
   git push -u origin main
   ```

3. **Thêm secret cho GitHub Actions**:
   - Vào repo trên GitHub → Settings → Secrets and variables → Actions → New repository secret.
   - Tên: `NTFY_TOPIC`, giá trị: tên topic bạn đã chọn ở bước 1.

4. **Kiểm tra**: vào tab Actions → chọn workflow "Check tax news" → Run workflow để chạy thử ngay, xem có nhận được thông báo trên app ntfy không.

## Tùy chỉnh

- Sửa danh sách `KEYWORDS` trong `scripts/check_tax_news.py` để thêm/bớt loại thuế cần theo dõi.
- Sửa dòng `cron` trong workflow để đổi tần suất chạy (hiện tại: mỗi tuần).
- Đổi `MAX_AGE_DAYS` (biến môi trường) nếu muốn nới/rút ngắn cửa sổ "tin mới".
