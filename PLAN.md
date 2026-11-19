# KẾ HOẠCH TRIỂN KHAI DỰ ÁN (PROJECT PLAN)
## HỆ THỐNG SỐ HÓA, TỰ ĐỘNG ĐỔI TÊN & TRA CỨU HỒ SƠ GPLX

---

## 1. LỘ TRÌNH TỔNG QUAN (ROADMAP)

Dự án được chia làm **5 giai đoạn (Phases)** tuần tự nhằm đảm bảo chất lượng, kiểm soát rủi ro về độ chính xác OCR và bàn giao sản phẩm hoàn chỉnh, thân thiện nhất cho người dùng không rành IT.

```mermaid
flowchart LR
    P1["Phase 1:\nCore OCR Engine &\nExcel Generator"] --> P2["Phase 2:\nDesktop UI &\nMàn hình Hậu kiểm"]
    P2 --> P3["Phase 3:\nCSDL SQLite &\nTra cứu nhảy trang"]
    P3 --> P4["Phase 4:\nChia sẻ LAN &\nĐa máy trạm"]
    P4 --> P5["Phase 5:\nĐóng gói Portable &\nKiểm thử thực tế"]
```

---

## 2. CHI TIẾT CÁC GIAI ĐOẠN (DETAILED PHASES)

### Giai đoạn 1: Xây dựng Lõi Xử lý OCR & Tự động Sinh Excel (Phase 1: Core Engine) - ĐÃ HOÀN THÀNH ✅
- **Mục tiêu**: Chạy thử nghiệm thành công trên các file PDF scan thực tế, tách được bảng, đọc được bìa và xuất ra file Excel chuẩn + tên file đề xuất + File Excel Tổng hợp cấp Tỉnh.
- **Các nhiệm vụ cụ thể**:
  - [x] Phân tích cấu trúc trang bìa và trang danh sách từ tài liệu mẫu thực tế.
  - [x] Xây dựng module trích xuất ảnh độ nét cao từ PDF (sử dụng `pypdfium2` & `Pillow` ở 200–300 DPI siêu nhanh).
  - [x] Phát hiện vùng bảng biểu và phân nhóm dòng/cột bằng Bounding Box Clustering (STT, Họ tên, Năm sinh, Địa chỉ, Số bằng).
  - [x] Tích hợp mô hình OCR chữ in tiếng Việt & số (RapidOCR ONNX CPU runtime) tối ưu cho máy tính văn phòng.
  - [x] Viết bộ lọc chuẩn hóa Regex: Tự động sửa lỗi nhầm lẫn ký tự số bằng (O/0, I/1, S/5, ...).
  - [x] Xây dựng module tự động sinh file `.xlsx` con bằng `openpyxl` với định dạng chuẩn form nhà nước.
  - [x] Lập trình logic đặt tên file: Ghép `[Mã tỉnh].[SQL].[Tháng].[Năm].[SốĐầu]-[SốCuối]`.
  - [x] **[MỚI BỔ SUNG] Module phân tích đường dẫn thư mục 3 cấp** (`src/folder_parser.py`): Tự động bóc tách thông tin HỘP (Tủ hồ sơ) và HỘP SỐ (Hộp giấy) từ cấu trúc `Tỉnh / Hộp / Hộp số / file.pdf`.
  - [x] **[MỚI BỔ SUNG] Thuật toán rà soát dãy số GPLX** (`src/sequence_analyzer.py`): Tự động gom các số liên tiếp thành dải `A-B`, tách các dải ngắt quãng bằng dấu `; `, đánh giá tính liên tục ("Đủ" vs "Ngắt, không theo thứ tự").
  - [x] **[MỚI BỔ SUNG] Module tạo & cập nhật File Excel Tổng Hợp Tỉnh** (`src/master_summary.py`): Tự động duy trì và cập nhật file `"SỔ THEO DÕI, RÀ SOÁT DÃY SỐ GPLX TRONG SỔ GỐC"` theo tỉnh với đầy đủ 12 cột chuẩn.
  - [x] Viết script kiểm thử đầu cuối `test_phase1.py` xử lý hoàn chỉnh tài liệu PDF scan mẫu và kiểm chứng file tổng hợp.
- **Sản phẩm đầu ra (Deliverables)**:
  - Script Python chạy kiểm thử độc lập: Nhận đầu vào là file PDF scan thô theo cấu trúc thư mục -> tự động nhận dạng bìa, đọc bảng, sinh file Excel con, đổi tên file PDF và cập nhật file Excel tổng hợp của tỉnh.

---

### Giai đoạn 2: Xây dựng Giao diện Desktop & Màn hình Hậu kiểm (Phase 2: Desktop UI & Review) - ĐÃ HOÀN THÀNH ✅
- **Mục tiêu**: Cung cấp giao diện trực quan cho nhân viên số hóa thực hiện nạp thư mục, kiểm tra nhanh và xác nhận đổi tên hàng loạt.
- **Các nhiệm vụ cụ thể**:
  - [x] Khởi tạo ứng dụng Desktop hoàn chỉnh bằng `CustomTkinter` (`src/gui/app.py` và `app_desktop.py`).
  - [x] **[MỚI] Mặc định mở toàn màn hình (Maximized Full Screen)**: Chiếm trọn màn hình máy tính ngay khi khởi chạy.
  - [x] **[MỚI] Giao diện Kéo giãn Đa năng (Resizable PanedWindow)**: Cho phép kéo sang trái/phải để tùy biến kích thước của 3 thành phần: Hàng đợi, PDF Preview và Xác nhận thông tin.
  - [x] **[MỚI] Cuộn ngang độc lập cho Trình xem PDF**: Tích hợp thanh cuộn ngang, cuộn dọc và hỗ trợ `Shift + Lăn chuột` duyệt ảnh scan khổ ngang mượt mà.
  - [x] **[MỚI] Hiệu ứng Icon Loading vòng tròn**: Hiển thị biểu tượng quay vòng tròn động trên nút OCR trong suốt thời gian tiến trình xử lý.
  - [x] **[MỚI] Cơ chế khóa / làm mờ (disable) nút bấm thông minh**:
    - [x] Nút *'Chạy OCR Tự Động'* tự làm mờ khi chưa upload file, tự bật sáng khi đã có file trong hàng đợi.
    - [x] Nút *'Xác nhận: Đổi tên PDF & Xuất Excel...'* tự làm mờ khi chưa chạy OCR xong, chỉ bật sáng khi dữ liệu đã sẵn sàng để đối soát.
  - [x] **[MỚI] Đổi màu nổi bật nút 'Chọn File PDF lẻ'**: Sử dụng màu xanh ngọc lục bảo (`#10B981`) bắt mắt, trực quan.
  - [x] **[MỚI] Lưu In-Place & Bảo toàn 100% file gốc**:
    - [x] Lưu file PDF chuẩn mới và file Excel con trực tiếp vào đúng thư mục tải lên (`os.path.dirname(original_path)`).
    - [x] Tuyệt đối không xóa hay sửa đổi file PDF scan gốc ban đầu.
    - [x] Tự động cập nhật file Excel Tổng hợp Tỉnh tại thư mục gốc Tỉnh (`find_province_root_dir`).
  - [x] Xây dựng màn hình **Hàng đợi Xử lý (Batch Queue)** (`src/gui/batch_queue.py`): Chọn thư mục, nạp cây thư mục Tỉnh/Hộp/Hộp số, hiển thị huy hiệu trạng thái (Chờ, Đang OCR, Chờ duyệt, Hoàn thành), thanh tiến độ và bộ chọn Tỉnh.
  - [x] Xây dựng màn hình **Đối soát Side-by-Side (Review & Edit)**:
    - [x] Nửa bên trái (`src/gui/pdf_viewer.py`): Khung xem trước file PDF độ nét cao, zoom in/out, xoay trang, nhảy trang.
    - [x] Nửa bên phải (`src/gui/review_panel.py`): Banner tên file đề xuất, form thông tin bìa (Loại sổ, Khóa, Ngày thi), **ô HỘP, HỘP SỐ**, **ô Rà soát dãy số & Ghi chú nhận định (Đủ vs Ngắt quãng)**, bảng dữ liệu công dân dạng ô nhập chỉnh sửa nhanh.
  - [x] Cơ chế tương tác nhảy trang: Bấm vào số trang `P.2` của công dân nào là PDF Viewer tự động cuộn đến chính xác trang đó.
  - [x] Nút bấm `1-Click Xác nhận`: Đổi tên file PDF + Tạo file Excel con + Cập nhật tự động dòng mới vào File Excel Tổng Hợp Tỉnh + Tự động chuyển trạng thái hàng đợi sang `Hoàn thành` và nạp file kế tiếp.
  - [x] Viết script kiểm thử tự động `test_phase2.py` kiểm chứng toàn bộ luồng tương tác giao diện và cập nhật dữ liệu.
- **Sản phẩm đầu ra (Deliverables)**:
  - Ứng dụng Desktop chạy độc lập qua lệnh `python app_desktop.py`, giao diện trực quan, chia 3 cột hiện đại, mở toàn màn hình, lưu in-place an toàn và xử lý đa luồng ngầm không đơ giật.

---

### Giai đoạn 3: CSDL SQLite Zero-Config & Tra cứu Nhảy Trang (Phase 3: Database & Search)
- **Mục tiêu**: Xây dựng kho tra cứu tức thì cho cán bộ tiếp dân, gõ tên/số bằng là tìm thấy ngay và mở đúng trang PDF.
- **Các nhiệm vụ cụ thể**:
  - [ ] Khởi tạo CSDL SQLite với bảng ảo `FTS5` (Full-Text Search) hỗ trợ tiếng Việt có dấu và không dấu.
  - [ ] Xây dựng bộ đồng bộ (Sync Pipeline): Khi một file PDF được xác nhận đổi tên ở Phase 2, tự động chèn dữ liệu toàn bộ công dân vào SQLite.
  - [ ] Xây dựng màn hình **Tra cứu Hồ sơ (Search Screen)**:
    - Ô tìm kiếm thông minh: Gõ số bằng, họ tên (không dấu/có dấu), năm sinh.
    - Bảng hiển thị danh sách kết quả tìm kiếm với độ trễ < 50ms.
  - [ ] Tích hợp **Trình xem PDF nội bộ (Built-in PDF.js)**:
    - Khi bấm nút `Xem PDF` ở dòng công dân tương ứng, app tự mở cửa sổ PDF và **tự động cuộn đến chính xác trang người đó xuất hiện**.
  - [ ] Thêm nút `Mở file Excel`, `Mở phần mềm ngoài`, `Mở thư mục chứa file trong Windows Explorer`.
  - [ ] Xây dựng tính năng `Quét lại dữ liệu từ Excel (Re-index)` để đồng bộ nếu người dùng sửa file Excel bằng tay.
- **Sản phẩm đầu ra (Deliverables)**:
  - Phân hệ tra cứu hoàn chỉnh, tìm kiếm và mở trực tiếp hồ sơ nhanh chóng.

---

### Giai đoạn 4: Tính năng Chia sẻ Mạng LAN Đa Máy (Phase 4: Multi-PC LAN Server)
- **Mục tiêu**: Cho phép nhiều máy tính trong cùng phòng làm việc cùng tra cứu dữ liệu từ một ổ SSD cắm ở máy chính.
- **Các nhiệm vụ cụ thể**:
  - [ ] Cấu hình Backend FastAPI hỗ trợ lắng nghe trên toàn bộ giao diện mạng nội bộ (`0.0.0.0:8080`).
  - [ ] Xây dựng giao diện Web Client (bản rút gọn chạy trên trình duyệt web Chrome/Edge dành cho các máy phụ).
  - [ ] Bổ sung nút gạt trên giao diện Desktop máy chính: `Bật / Tắt chia sẻ mạng nội bộ`.
  - [ ] Tự động lấy IP máy chính trong mạng LAN (VD: `192.168.1.25:8080`) và hiển thị mã QR trên màn hình để nhân viên khác kết nối.
  - [ ] Cơ chế stream file PDF qua mạng LAN an toàn, mượt mà khi nhiều máy cùng mở file cùng lúc.
- **Sản phẩm đầu ra (Deliverables)**:
  - Máy chính cắm ổ SSD mở app; máy phụ chỉ cần mở Chrome gõ địa chỉ IP là tìm kiếm và xem PDF bình thường.

---

### Giai đoạn 5: Đóng gói Portable, Tối ưu & Bàn giao (Phase 5: Packaging & Handover)
- **Mục tiêu**: Đóng gói thành bản Portable duy nhất nằm gọn trên ổ SSD, cắm vào máy tính là chạy; hướng dẫn sử dụng chi tiết.
- **Các nhiệm vụ cụ thể**:
  - [ ] Đóng gói toàn bộ mã nguồn, model AI, môi trường Python thành một thư mục Portable (dùng PyInstaller / Inno Setup).
  - [ ] Tối ưu hóa dung lượng model AI và tốc độ chạy trên CPU máy văn phòng (RAM 8GB, không GPU).
  - [ ] Thử nghiệm Stress Test: Quét và xử lý liên tục 50 - 100 cuốn sổ PDF (tương đương 500 - 1.000 trang).
  - [ ] Viết tài liệu hướng dẫn sử dụng nhanh dạng hình ảnh (Quick User Guide).
  - [ ] Bàn giao và nghiệm thu.

---

## 3. MA TRẬN RỦI RO & PHƯƠNG ÁN XỬ LÝ (RISK MATRIX)

| Rủi ro | Mức độ | Phương án xử lý |
| :--- | :---: | :--- |
| **Chữ viết tay số bằng quá mờ hoặc nét viết dị dạng** | Trung bình | - Hệ thống áp dụng quy tắc Regex bắt buộc định dạng chuẩn.<br>- Đánh dấu màu vàng cảnh báo để người dùng kiểm tra nhanh trong 2 giây trên màn hình hậu kiểm trước khi xác nhận đổi tên. |
| **Người dùng vô tình sửa trực tiếp file Excel ngoài desktop làm lệch CSDL** | Thấp | Cung cấp nút `Quét & Đồng bộ lại từ Excel` trong màn hình Cài đặt, tự động cập nhật lại SQLite từ các file `.xlsx` trên ổ SSD. |
| **Mất điện hoặc tắt máy đột ngột khi đang xử lý** | Thấp | Cơ chế ghi file Atomic (đổi tên tạm sang file `.tmp`, thành công mới ghi đè tên chuẩn). File PDF gốc luôn được bảo vệ an toàn. |
| **Máy tính văn phòng cấu hình yếu (CPU Core i3/i5 cũ, RAM 4GB-8GB)** | Trung bình | Tối ưu mô hình OCR dạng Mobile/Lightweight (chỉ nặng ~15MB - 30MB), sử dụng ONNX Runtime đa luồng CPU, tốc độ xử lý chỉ 1.5s/trang. |
| **Xung đột tên file khi đổi tên** | Thấp | Tự động kiểm tra nếu trùng tên file đã có, hệ thống sẽ thêm hậu tố `_1`, `_2` hoặc thông báo cho nhân viên kiểm tra. |
