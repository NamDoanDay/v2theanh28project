# SỔ TAY HƯỚNG DẪN SỬ DỤNG HỆ THỐNG
## PHẦN MỀM SỐ HÓA, TỰ ĐỘNG ĐỔI TÊN & TRA CỨU HỒ SƠ GIẤY PHÉP LÁI XE (GPLX LỊCH SỬ)

---

## 1. GIỚI THIỆU TỔNG QUAN

Hệ thống được thiết kế chuyên biệt phục vụ công tác số hóa, lưu trữ và tra cứu hồ sơ cấp GPLX cơ giới đường bộ (giai đoạn trước năm 2012) theo tiêu chuẩn lưu trữ quốc gia.

### 🌟 Ưu điểm nổi bật của Hệ thống:
1. **Chạy Trực Tiếp từ Ổ Cứng Di Động (Zero-Config Portable)**: Cắm ổ SSD/USB vào bất kỳ máy tính Windows nào là chạy ngay, không cần cài đặt SQL Server hay phần mềm phụ trợ.
2. **Bảo Toàn 100% Tệp Gốc (In-Place Safety)**: File mới đổi tên và file Excel được tạo ngay tại thư mục chứa file scan, **tuyệt đối không xóa hay thay đổi file gốc ban đầu**.
3. **Quy Tắc Đặt Tên Chuẩn**: Tự động đặt tên theo cấu trúc: `[Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf`.
4. **Tiếng Việt Có Dấu Đầy Đủ**: Tự động phục hồi và chuẩn hóa dấu tiếng Việt chuẩn cho Họ tên, Địa chỉ, Quốc tịch.
5. **Tra Cứu Siêu Tốc & Nhảy Trang PDF**: Tìm kiếm < 1ms, bấm vào người dân là lật đến chính xác trang có số bằng trong sổ scan.
6. **Theo Dõi Danh Mục Hồ Sơ Đã Import**: Quản lý chi tiết theo Tỉnh -> Hộp (Tủ) -> Hộp số (Hồ sơ) -> File Excel/PDF đã nạp.
7. **Chia Sẻ Mạng Nội Bộ (LAN Server)**: Máy chính bật chia sẻ, các máy phụ trong phòng chỉ cần mở Chrome/Edge hoặc quét mã QR là tra cứu được ngay.

---

## 2. CẤU TRÚC DỮ LIỆU TRÊN Ổ CỨNG SSD

Dữ liệu trên ổ cứng di động được tổ chức theo cấu trúc phân cấp chuẩn:
```text
[Ổ_CỨNG_SSD]:\
├── 🚀 Chay_UngDung_GPLX.bat                <-- File chạy 1-Click mở ứng dụng
├── 📁 DuLieu_GPLX/                         <-- Kho tài liệu số hóa theo tỉnh
│   └── 📁 LaoCai/                         <-- Cấp Tỉnh (Ví dụ: Mã 15)
│       ├── So_Theo_Doi_Day_So_GPLX_15.xlsx <-- Sổ theo dõi dãy số GPLX cấp Tỉnh
│       └── 📁 HOP_48/                     <-- Cấp Hộp (Tủ hồ sơ)
│           └── 📁 HOP_SO_115/             <-- Cấp Hộp Số (Hộp giấy)
│               ├── scan_001.pdf           <-- File scan gốc ban đầu (Được giữ nguyên)
│               ├── 15.SQL.03.1996.A461544-C244140.pdf  <-- File PDF chuẩn mới
│               └── 15.SQL.03.1996.A461544-C244140.xlsx <-- File Excel danh sách kèm theo
└── 📁 HeThong/                             <-- CSDL tìm kiếm nội bộ
    └── gplx_index.db                      <-- SQLite FTS5 (Không xóa tệp này)
```

---

## 3. HƯỚNG DẪN KHỞI CHẠY ỨNG DỤNG (1-CLICK)

1. Cắm ổ cứng SSD di động vào cổng USB máy tính.
2. Mở ổ đĩa SSD, nhấp đúp chuột vào file:
   $$\text{🚀 Chay\_UngDung\_GPLX.bat}$$
3. Màn hình ứng dụng sẽ tự động mở lên ở chế độ **Toàn màn hình (Maximized)** sẵn sàng làm việc.

---

## 4. QUY TRÌNH SỐ HÓA, ĐỐI SOÁT & ĐỔI TÊN HỒ SƠ (TAB 1)

Giao diện Tab 1 gồm **3 cột làm việc trực quan** có thể kéo giãn linh hoạt sang trái/phải:

```text
┌───────────────────────┬───────────────────────────────┬───────────────────────────────┐
│  CỘT 1: HÀNG ĐỢI      │  CỘT 2: XEM TRƯỚC BẢN SCAN    │  CỘT 3: HẬU KIỂM & XÁC NHẬN  │
│  - Chọn tỉnh          │  - Phóng to / Thu nhỏ         │  - Tên file chuẩn đề xuất     │
│  - Chọn thư mục       │  - Xoay trang                 │  - Thông tin Bìa & Hộp/Hộp số │
│  - Nút đổi tên folder │  - Cuộn dọc & Cuộn ngang      │  - Bảng người dân (Có dấu)    │
│  - Nút chạy OCR       │  - Tự động nhảy trang         │  - Nút 1-Click Xác Nhận       │
└───────────────────────┴───────────────────────────────┴───────────────────────────────┘
```

### Các bước thực hiện:
* **Bước 1: Nạp hồ sơ**:
  * Chọn Mã Tỉnh tương ứng (Mặc định: `15 - Tỉnh Lào Cai`).
  * Bấm `📁 Chọn Thư mục Hồ sơ` để nạp toàn bộ các cuốn sổ scan trong thư mục vào hàng đợi, hoặc bấm `📄 Chọn File PDF lẻ` (màu xanh lá) để thêm từng file.
* **Bước 2: Chạy OCR**:
  * Bấm nút `⚡ Chạy OCR Tự Động`. Nút sẽ hiển thị icon xoay vòng tròn động báo hiệu đang xử lý ngầm.
  * Khi xử lý xong, trạng thái file chuyển sang `CHỜ DUYỆT (READY)`.
* **Bước 3: Đối soát thông tin**:
  * Chọn cuốn sổ trong hàng đợi để xem.
  * Cột 2 hiển thị bản scan gốc (hỗ trợ cuộn ngang bằng `Shift + Lăn chuột` với bản scan khổ ngang).
  * Cột 3 hiển thị thông tin trích xuất: Loại sổ, Khóa thi, Ngày bìa, HỘP, HỘP SỐ, Nhận định dãy số ("Đủ" vs "Ngắt").
  * Bấm vào số trang `P.2` của bất kỳ công dân nào để xem ngay bản scan tương ứng.
* **Bước 4: Xác nhận & Lưu In-Place**:
  * Bấm nút lớn: **`💾 Xác nhận: Đổi tên PDF & Xuất Excel & Cập nhật Tổng hợp`**.
  * Hệ thống tự động:
    1. Tạo file PDF chuẩn mới mang tên quy định tại đúng thư mục đó.
    2. Tạo file Excel con tương ứng với STT chạy tuần tự 1..N và tiếng Việt có dấu.
    3. Cập nhật dòng mới vào File Excel Tổng Hợp Cấp Tỉnh.
    4. Giữ nguyên 100% file gốc cũ.
    5. Đồng bộ tức thì vào CSDL SQLite phục vụ tra cứu.

---

## 5. TÍNH NĂNG ĐỔI TÊN FILE THEO FOLDER (FAST OCR SIÊU TỐC)

Dành cho nhu cầu **chỉ cần copy và đổi tên hàng loạt file PDF** trong thư mục mà không cần xuất file Excel con:

1. Tại khung *Hàng đợi hồ sơ*, bấm nút: **`📑 Đổi tên file (theo folder)`** (màu vàng cam).
2. Chọn thư mục chứa các file PDF scan cần đổi tên.
3. Hệ thống kích hoạt **Thuật toán Fast OCR Tối Ưu**:
   * Chỉ đọc đúng 3 trang: **Trang 1 (Bìa)** + **Trang 2 (Hàng 1)** + **Trang cuối (Hàng cuối)**.
   * Bỏ qua hoàn toàn các trang từ 3 đến N-1.
   * Tốc độ xử lý chỉ mất **~2-3 giây/file** (nhanh gấp 20 lần).
4. Tự động copy và sinh file mới tên chuẩn tại thư mục đó, giữ nguyên file gốc cũ.

---

## 6. HƯỚNG DẪN TRA CỨU HỒ SƠ & MỞ FILE SCAN (TAB 2)

Tại Tab 2, hệ thống cung cấp **Bộ chuyển đổi 2 Chế độ xem linh hoạt**:

### Chế độ 1: 👤 Tra Cứu Công Dân
* **Ô tìm kiếm thông minh**: Gõ bất kỳ thông tin nào:
  * Số bằng: `A461544`, `C244138`...
  * Họ tên (có dấu hoặc không dấu): `trần văn yên` hoặc `tran van yen`...
  * Năm sinh: `1960`, `1968`...
* **Kết quả**: Trả về trong vòng **< 1 mili-giây**.
* **Thao tác nhanh trên mỗi dòng**:
  * `👁️ Xem PDF (P.X)`: Mở trực tiếp và lật đúng trang scan chứa tên người lái xe.
  * `📊 Excel`: Mở ngay file Excel con bằng Microsoft Excel.
  * `📂 Thư mục`: Mở thư mục chứa file trong Windows Explorer và tự động trỏ vào file.

### Chế độ 2: 📁 Danh Mục Sổ / File Excel Đã Import
* **Thống kê tổng quan**: Nắm rõ ngay trong hệ thống hiện có bao nhiêu Tỉnh, bao nhiêu Hộp, bao nhiêu Hộp số và tổng bao nhiêu cuốn sổ/file Excel đã nạp.
* **Bảng theo dõi chi tiết**: Liệt kê từng file Excel kèm HỘP, HỘP SỐ, Ngày bìa, Hạng, Số lượng GPLX.
* **Nút `👥 Xem Dân`**: Bấm vào nút này để lọc ngay danh sách toàn bộ người dân trong cuốn sổ đó!

---

## 7. HƯỚNG DẪN CHIA SẺ MẠNG LAN CHO MÁY PHỤ (TAB 3)

Cho phép các máy tính khác hoặc máy tính bảng/điện thoại trong cùng phòng cùng tra cứu mà không cần cắm ổ SSD:

1. Tại máy tính chính (máy cắm ổ SSD), mở Tab: **`🌐 CHIA SẺ MẠNG LAN`**.
2. Bấm nút: **`▶ BẬT CHIA SẺ MẠNG LAN`**.
3. Màn hình hiển thị:
   * Địa chỉ truy cập nội bộ (Ví dụ: `http://192.168.1.15:8080`).
   * Mã **QR Code** kết nối tức thì.
4. **Trên các máy tính phụ hoặc điện thoại**:
   * Mở trình duyệt web Google Chrome hoặc Microsoft Edge.
   * Gõ địa chỉ IP hiển thị trên màn hình máy chính (hoặc dùng camera quét mã QR).
   * Giao diện tra cứu web hiện ra tức thì, hoạt động 100% offline, cho phép tìm kiếm, xem trang PDF nhúng và tải file Excel về máy phụ.

---

## 8. BẢNG MÃ TỈNH CẤP 1 & QUY TẮC ĐẶT TÊN CHUẨN

* **Định dạng chuẩn**: `[Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf`
* **Một số mã tỉnh tiêu biểu**:
  * `15`: Tỉnh Lào Cai
  * `01`: Thành phố Hà Nội
  * `79`: Thành phố Hồ Chí Minh
  * `19`: Tỉnh Phú Thọ
  * `21`: Tỉnh Yên Bái
  * `20`: Tỉnh Thái Nguyên
  * `22`: Tỉnh Tuyên Quang
  * `24`: Tỉnh Hà Giang
  * `11`: Tỉnh Lạng Sơn
  * `14`: Tỉnh Quảng Ninh

---

## 9. XỬ LÝ SỰ CỐ THƯỜNG GẶP (FAQ)

1. **Hỏi**: Nếu tôi sửa trực tiếp file Excel con bằng Microsoft Excel ngoài desktop thì CSDL có cập nhật không?
   * **Trả lời**: Có. Bạn chỉ cần vào Tab Tra Cứu, bấm nút **`🔄 Quét lại từ Excel`** và chọn thư mục, hệ thống sẽ tự động đồng bộ lại toàn bộ dữ liệu mới nhất vào SQLite.
2. **Hỏi**: File PDF gốc ban đầu của tôi có bị xóa mất sau khi đổi tên không?
   * **Trả lời**: Tuyệt đối không. Hệ thống áp dụng cơ chế sao chép an toàn (Safe Copy), file scan gốc cũ luôn được giữ nguyên 100%.
3. **Hỏi**: Máy phụ trong phòng không kết nối được vào địa chỉ mạng LAN?
   * **Trả lời**: Đảm bảo cả máy chính và máy phụ đang bắt chung một mạng Wi-Fi hoặc cùng cắm dây mạng LAN của cơ quan. Kiểm tra xem nút Bật Chia Sẻ Mạng LAN trên máy chính đã chuyển sang màu đỏ (Đang phát) hay chưa.
