# SỔ TAY HƯỚNG DẪN SỬ DỤNG HỆ THỐNG
## PHẦN MỀM SỐ HÓA, TỰ ĐỘNG ĐỔI TÊN & TRA CỨU HỒ SƠ GIẤY PHÉP LÁI XE (GPLX LỊCH SỬ)
*Dành riêng cho người dùng nghiệp vụ và chuyên viên số hóa (Không yêu cầu kiến thức Công nghệ thông tin)*

---

## 1. GIỚI THIỆU TỔNG QUAN

Hệ thống được thiết kế chuyên biệt phục vụ công tác số hóa, lưu trữ, quản lý và tra cứu hồ sơ cấp GPLX cơ giới đường bộ (giai đoạn trước năm 2012) theo tiêu chuẩn lưu trữ quốc gia.

### 🌟 Ưu điểm nổi bật của Hệ thống:
1. **Bàn Giao Trọn Gói 1-Click (Dành cho Non-IT)**: Toàn bộ hệ thống nằm gọn trong thư mục `So Hoa GPLX`. Chỉ cần **nhấp đúp chuột vào `Chay_Ngay.bat`** là ứng dụng tự mở và chạy ngay lập tức. Không cần cài đặt Python, không cần gõ lệnh.
2. **Cấu Trúc Kho Lưu Trữ Tự Động Phân Cấp**:
   - Tự động sinh ra cây thư mục: `DuLieuSoHoa_GPLS -> [Tên_Tỉnh] -> HOP_[Số_Hộp] -> HoSo_[Số_Hồ_Sơ]`.
   - Đáp ứng trọn vẹn quy trình phân loại lưu trữ hồ sơ của Cục Đường bộ và Sở Giao thông Vận tải.
3. **Bảo Toàn 100% Tệp Gốc (In-Place Safety)**: File mới đổi tên và file Excel được tạo ngay tại thư mục chứa file scan, **tuyệt đối không xóa hay thay đổi file gốc ban đầu**.
4. **Quy Tắc Đặt Tên Chuẩn**: Tự động đặt tên theo cấu trúc: `[Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf`.
5. **Tiếng Việt Có Dấu Đầy Đủ**: Tự động phục hồi và chuẩn hóa dấu tiếng Việt chuẩn cho Họ tên, Địa chỉ, Quốc tịch theo nguyên tắc ghép từ có nghĩa.
6. **Thuật Toán Fast OCR Siêu Tốc**: Chức năng đổi tên theo folder chỉ mất 2-3 giây/file vì chỉ đọc 3 trang cốt lõi (Bìa, Dòng 1 Trang 2, Dòng cuối Trang cuối).
7. **Tra Cứu Siêu Tốc & Nhảy Trang PDF**: Tìm kiếm < 1ms, bấm vào người dân là lật đến chính xác trang có số bằng trong sổ scan.
8. **Theo Dõi Danh Mục Hồ Sơ Đã Import**: Quản lý chi tiết theo Tỉnh -> Hộp (Tủ) -> Hộp số (Hồ sơ) -> File Excel/PDF đã nạp, có nút `👥 Xem Dân` lọc ngay danh sách công dân trong sổ.
9. **Chia Sẻ Mạng Nội Bộ (LAN Server)**: Máy chính bật chia sẻ, các máy phụ trong phòng chỉ cần mở Chrome/Edge hoặc quét mã QR là tra cứu được ngay.

---

## 2. CẤU TRÚC THƯ MỤC BÀN GIAO CHUẨN

Gói ứng dụng bàn giao cho người dùng được tổ chức tại thư mục:
```text
📁 So Hoa GPLX/
│
├── 🚀 Chay_Ngay.bat                 <-- [QUAN TRỌNG] Nhấp đúp chuột vào đây để chạy ứng dụng
│
├── 📁 app/                          <-- Thư mục chứa phần mềm độc lập (.exe)
│   ├── GPLX_SoHoa_TraCuu.exe        <-- Tệp thực thi chính của ứng dụng
│   ├── _internal/                   <-- Các thư viện nhúng (AI OCR, PDF engine, SQLite)
│   └── data/                        <-- Bảng mã danh mục tỉnh thành toàn quốc
│
└── 📁 DuLieuSoHoa_GPLS/             <-- KHO LƯU TRỮ HỒ SƠ SỐ HÓA THEO TỈNH
    ├── HUONG_DAN_LUU_TRU.txt        <-- Ghi chú hướng dẫn cho cán bộ số hóa
    │
    ├── 📁 LaoCai/                   <-- Tỉnh Lào Cai (Mã 15)
    │   └── 📁 HOP_01/               <-- Tủ / Hộp số 01
    │       └── 📁 HoSo_01/          <-- Tập hồ sơ 01 (Nơi để các file scan PDF)
    │           ├── sample_input.pdf                     <-- File scan gốc (giữ nguyên)
    │           ├── 15.SQL.03.1996.A461544-C244140.pdf   <-- File PDF đổi tên chuẩn
    │           └── 15.SQL.03.1996.A461544-C244140.xlsx  <-- Danh sách công dân trích xuất
    │
    ├── 📁 TuyenQuang/
    │   └── 📁 HOP_01/
    │       └── 📁 HoSo_01/
    │
    ├── 📁 DienBien/
    │   └── 📁 HOP_01/
    │       └── 📁 HoSo_01/
    │
    ├── 📁 SonLa/
    │   └── 📁 HOP_01/
    │       └── 📁 HoSo_01/
    │
    ├── 📁 HaGiang/
    ├── 📁 YenBai/
    ├── 📁 CaoBang/
    ├── 📁 LangSon/
    ├── 📁 PhuTho/
    ├── 📁 BacKan/
    ├── 📁 HoaBinh/
    └── 📁 LaiChau/
        └── 📁 HOP_01/
            └── 📁 HoSo_01/
```

> [!NOTE]
> Khi mở ứng dụng lần đầu, nếu phát hiện thư mục tỉnh hay hộp nào chưa có, phần mềm sẽ **tự động khởi tạo đầy đủ** cây thư mục chuẩn trên.

---

## 3. HƯỚNG DẪN KHỞI CHẠY ỨNG DỤNG (DÀNH CHO NGƯỜI DÙNG KHÔNG BIẾT IT)

1. Mở thư mục **`So Hoa GPLX`** (trên màn hình Desktop hoặc trên ổ cứng cắm ngoài).
2. Nhấp đúp chuột trái vào tệp:
   $$\text{🚀 \textbf{Chay\_Ngay.bat}}$$
3. Hệ thống sẽ khởi động ứng dụng và phóng to toàn màn hình. Bạn đã sẵn sàng làm việc mà không cần cài đặt thêm bất kỳ phần mềm nào khác!

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

### Các bước thực hiện chi tiết:
* **Bước 1: Chọn tỉnh và nạp file**:
  * Chọn Mã Tỉnh trong menu thả xuống (Mặc định: `15 - Tỉnh Lào Cai`).
  * Bấm nút **`📁 Chọn Thư mục Hồ sơ`** để đưa toàn bộ file PDF trong một tập hồ sơ vào hàng đợi. Cửa sổ chọn thư mục sẽ tự động mở thẳng vào `DuLieuSoHoa_GPLS`.
  * Hoặc bấm nút **`📄 Chọn File PDF lẻ`** (màu xanh lá) để thêm từng file riêng biệt.
* **Bước 2: Chạy OCR trích xuất**:
  * Bấm nút **`⚡ Chạy OCR Tự Động`**.
  * Nút chuyển trạng thái xoay vòng tròn báo hiệu tiến trình đang đọc tự động nền ngầm.
  * Khi xử lý xong, trạng thái file chuyển sang `CHỜ DUYỆT (READY)`.
* **Bước 3: Đối soát bản scan và dữ liệu**:
  * Nhấp chuột vào tên cuốn sổ ở Cột 1 để xem chi tiết.
  * Cột 2 hiển thị bản scan gốc (hỗ trợ cuộn ngang bằng `Shift + Con lăn chuột` với văn bản khổ A3 nằm ngang).
  * Cột 3 hiển thị thông tin trích xuất: Loại sổ, Khóa thi, Ngày bìa, HỘP, HỘP SỐ, Nhận định dãy số ("Đủ" vs "Ngắt").
  * Nhấp chuột vào số trang `P.2`, `P.3` của bất kỳ công dân nào để xem ngay trang scan có số bằng tương ứng.
* **Bước 4: Xác nhận & Lưu In-Place**:
  * Bấm nút: **`💾 Xác nhận: Đổi tên PDF & Xuất Excel & Cập nhật Tổng hợp`**.
  * Hệ thống tự động:
    1. Tạo file PDF chuẩn mới mang tên quy định tại đúng thư mục đó.
    2. Tạo file Excel con tương ứng với STT chạy tuần tự 1..N và tiếng Việt có dấu chuẩn xác.
    3. Cập nhật dòng mới vào File Excel Tổng Hợp Cấp Tỉnh.
    4. Giữ nguyên 100% file gốc cũ.
    5. Đồng bộ tức thì vào CSDL SQLite phục vụ tra cứu.

---

## 5. TÍNH NĂNG ĐỔI TÊN FILE THEO FOLDER (FAST OCR SIÊU TỐC)

Dành cho nhu cầu **chỉ cần copy và đổi tên hàng loạt file PDF** trong thư mục mà không cần xuất file Excel con:

1. Tại khung *Hàng đợi hồ sơ*, bấm nút: **`📑 Đổi tên file (theo folder)`** (màu vàng cam).
2. Chọn thư mục hồ sơ (Ví dụ: `DuLieuSoHoa_GPLS/LaoCai/HOP_01/HoSo_01`).
3. Hệ thống kích hoạt **Thuật toán Fast OCR Tối Ưu**:
   * Chỉ đọc đúng 3 trang: **Trang 1 (Bìa)** + **Trang 2 (Dòng 1 lấy Số bằng đầu)** + **Trang cuối (Dòng cuối lấy Số bằng cuối)**.
   * Bỏ qua hoàn toàn các trang từ 3 đến N-1.
   * Tốc độ xử lý chỉ mất **~2-3 giây/file** (nhanh gấp 20 lần so với đọc toàn bộ trang).
4. Tự động sao chép và sinh file mới mang tên chuẩn tại thư mục đó:
   - Ví dụ: `15.SQL.03.1996.A461544-C244140.pdf`
   - File gốc ban đầu được giữ nguyên 100%.

---

## 6. HƯỚNG DẪN TRA CỨU HỒ SƠ & MỞ FILE SCAN (TAB 2)

Tại Tab 2, hệ thống cung cấp **Bộ chuyển đổi 2 Chế độ xem linh hoạt**:

### Chế độ 1: 👤 Tra Cứu Công Dân
* **Ô tìm kiếm thông minh**: Gõ bất kỳ thông tin nào:
  * Số bằng: `A461544`, `C244138`...
  * Họ tên (có dấu hoặc không dấu): `trần văn yên` hoặc `tran van yen`...
  * Năm sinh: `1960`, `1968`...
* **Tốc độ**: Trả về kết quả trong vòng **< 1 mili-giây** nhờ chỉ mục FTS5.
* **Thao tác nhanh trên mỗi dòng kết quả**:
  * `👁️ Xem PDF (P.X)`: Mở trực tiếp và lật đúng trang scan chứa tên người lái xe.
  * `📊 Excel`: Mở ngay file Excel con bằng Microsoft Excel.
  * `📂 Thư mục`: Mở thư mục chứa file trong Windows Explorer và tự động trỏ vào file.

### Chế độ 2: 📁 Danh Mục Sổ / File Excel Đã Import
* **Thống kê tổng quan**: Nắm rõ ngay trong hệ thống hiện có bao nhiêu Tỉnh, bao nhiêu Hộp, bao nhiêu Hộp số và tổng bao nhiêu cuốn sổ/file Excel đã nạp.
* **Bảng theo dõi chi tiết**: Liệt kê từng file Excel kèm HỘP, HỘP SỐ, Ngày bìa, Hạng bằng, Số lượng GPLX.
* **Nút `👥 Xem Dân`**: Bấm vào nút này để lọc ngay danh sách toàn bộ người dân trong cuốn sổ đó!

---

## 7. HƯỚNG DẪN CHIA SẺ MẠNG LAN CHO MÁY PHỤ (TAB 3)

Cho phép các máy tính khác hoặc máy tính bảng/điện thoại trong cùng phòng cùng tra cứu mà không cần cắm ổ cứng:

1. Tại máy tính chính (máy chạy ứng dụng), mở Tab: **`🌐 CHIA SẺ MẠNG LAN`**.
2. Bấm nút: **`▶ BẬT CHIA SẺ MẠNG LAN`**.
3. Màn hình hiển thị:
   * Địa chỉ truy cập nội bộ (Ví dụ: `http://192.168.1.15:8080`).
   * Mã **QR Code** kết nối tức thì.
4. **Trên các máy tính phụ hoặc điện thoại**:
   * Mở trình duyệt web Google Chrome hoặc Microsoft Edge.
   * Gõ địa chỉ IP hiển thị trên màn hình máy chính (hoặc dùng camera quét mã QR).
   * Giao diện tra cứu web hiện ra tức thì, hoạt động 100% offline, cho phép tìm kiếm, xem trang PDF nhúng và tải file Excel về máy phụ.

---

## 8. BẢNG MÃ TỈNH TIÊU BIỂU & QUY TẮC ĐẶT TÊN CHUẨN

* **Định dạng chuẩn**: `[Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf`
  * Dấu chấm `.` phân tách giữa các trường thông tin.
  * Dấu gạch ngang `-` **chỉ sử dụng duy nhất** giữa số bằng đầu và số bằng cuối.
* **Bảng mã tỉnh phổ biến**:
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
  * `12`: Tỉnh Cao Bằng
  * `27`: Tỉnh Điện Biên
  * `26`: Tỉnh Sơn La
  * `25`: Tỉnh Lai Châu
  * `28`: Tỉnh Hòa Bình
  * `06`: Tỉnh Bắc Kạn

---

## 9. XỬ LÝ SỰ CỐ THƯỜNG GẶP (FAQ)

1. **Hỏi**: Nếu tôi sửa trực tiếp file Excel con bằng Microsoft Excel ngoài desktop thì CSDL có cập nhật không?
   * **Trả lời**: Có. Bạn chỉ cần vào Tab Tra Cứu, bấm nút **`🔄 Quét lại từ Excel`** và chọn thư mục, hệ thống sẽ tự động đồng bộ lại toàn bộ dữ liệu mới nhất vào SQLite.
2. **Hỏi**: File PDF gốc ban đầu của tôi có bị xóa mất sau khi đổi tên không?
   * **Trả lời**: Tuyệt đối không. Hệ thống áp dụng cơ chế sao chép an toàn (Safe Copy), file scan gốc cũ luôn được giữ nguyên 100%.
3. **Hỏi**: Máy phụ trong phòng không kết nối được vào địa chỉ mạng LAN?
   * **Trả lời**: Đảm bảo cả máy chính và máy phụ đang bắt chung một mạng Wi-Fi hoặc cùng cắm dây mạng LAN của cơ quan. Kiểm tra xem nút Bật Chia Sẻ Mạng LAN trên máy chính đã chuyển sang màu đỏ (Đang phát) hay chưa.
4. **Hỏi**: Tôi muốn thêm một tỉnh mới hoặc hộp mới vào kho `DuLieuSoHoa_GPLS` thì làm thế nào?
   * **Trả lời**: Bạn chỉ cần tạo thư mục mới trực tiếp trong `DuLieuSoHoa_GPLS` theo cấu trúc: `[TênTỉnh]/HOP_[Số]/HoSo_[Số]` rồi đặt file scan vào, phần mềm sẽ tự nhận diện ngay.
