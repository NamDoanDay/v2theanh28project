"""
Automated Verification Script for Phase 2: Desktop GUI & Review Components.
"""
import os
import sys
from tkinter import messagebox

# Mock messagebox to avoid modal popups during headless test
messagebox.showinfo = lambda title, message: print(f"  [POPUP INFO] {title}: {message.splitlines()[0]}")
messagebox.showerror = lambda title, message: print(f"  [POPUP ERROR] {title}: {message.splitlines()[0]}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import GPLXApp
from src.config import DEFAULT_OUTPUT_DIR

def run_test():
    print("=" * 60)
    print("BẮT ĐẦU KIỂM THỬ TỰ ĐỘNG GIAI ĐOẠN 2: DESKTOP UI & REVIEW PANEL")
    print("=" * 60)

    sample_pdf = os.path.join(os.path.dirname(__file__), "samples", "LaoCai", "HOP_48", "HOP_SO_115", "sample_input.pdf")
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return False

    # 1. Initialize App in headless / hidden mode
    print("[1] Khởi tạo giao diện ứng dụng GPLXApp...")
    app = GPLXApp()
    app.withdraw() # Hide window for test

    try:
        # 2. Check initial button states & Resizable PanedWindow
        print("[2] Kiểm tra giao diện kéo giãn 3 cột (PanedWindow) & trạng thái nút...")
        assert hasattr(app, "paned"), "App must contain a PanedWindow"
        assert len(app.paned.panes()) == 3, "PanedWindow must contain 3 resizable panes"
        assert hasattr(app.viewer, "h_scrollbar"), "PDF Viewer must have a horizontal scrollbar"
        assert hasattr(app.viewer, "v_scrollbar"), "PDF Viewer must have a vertical scrollbar"
        print("  -> Đã xác thực giao diện kéo giãn 3 cột: Hàng đợi | PDF Preview | Màn hình Đối soát.")
        print("  -> Đã xác thực Trình xem PDF hỗ trợ cuộn 2 chiều (Cả cuộn Ngang và cuộn Dọc).")

        assert app.sidebar.btn_run_batch.cget("state") == "disabled", "btn_run_batch must be disabled initially"
        assert app.review.btn_confirm.cget("state") == "disabled", "btn_confirm must be disabled initially"
        print("  -> Nút 'Chạy OCR tự động' đang bị disable chuẩn xác khi chưa nạp file.")
        print("  -> Nút 'Xác nhận: Đổi tên...' đang bị disable chuẩn xác khi chưa chạy OCR.")

        # Test Spinner Animation
        app.sidebar.start_loading()
        assert app.sidebar.is_loading is True
        print("  -> Icon loading vòng tròn hoạt động chuẩn xác trên nút OCR:", app.sidebar.btn_run_batch.cget("text"))
        app.sidebar.stop_loading()
        assert app.sidebar.is_loading is False

        # 3. Add sample file to Batch Queue
        print(f"\n[3] Nạp tệp mẫu vào Hàng Đợi (Batch Queue): {sample_pdf}")
        app.sidebar._add_files_to_queue([sample_pdf])
        assert len(app.sidebar.queue_items) == 1, "Queue items count must be 1"
        assert app.sidebar.btn_run_batch.cget("state") == "normal", "btn_run_batch must be enabled after adding files"
        print("  -> Thêm vào hàng đợi thành công. Nút 'Chạy OCR tự động' đã được kích hoạt sáng!")

        # 4. Simulate File Selection & Loading into Viewer & Review Panel
        print("\n[4] Kiểm tra nạp file vào Trình xem PDF (PDFViewerFrame)...")
        app.viewer.load_pdf(sample_pdf, initial_page=1)
        assert app.viewer.total_pages == 2, f"Expected 2 pages, got {app.viewer.total_pages}"
        print(f"  -> Trình xem PDF tải thành công {app.viewer.total_pages} trang.")

        # 5. Simulate Processed Data Injection into Review Panel
        print("\n[5] Kiểm tra nạp dữ liệu bóc tách vào Màn hình Đối soát (ReviewPanel)...")
        from src.pipeline import process_dossier_pdf
        dossier_data = process_dossier_pdf(sample_pdf, default_province="15")
        app.review.load_data(dossier_data)

        # Verify button is now enabled
        assert app.review.btn_confirm.cget("state") == "normal", "btn_confirm must be enabled after OCR is loaded"
        print("  -> Nút 'Xác nhận: Đổi tên...' đã được kích hoạt sáng sau khi nạp kết quả OCR!")

        # Verify fields in Review Panel
        assert app.review.txt_proposed_filename.get() == dossier_data["proposed_filename"]
        assert app.review.txt_box.get() == "48"
        assert app.review.txt_box_number.get() == "115"
        assert app.review.txt_hang.get() == "A1"
        assert len(app.review.citizen_entries) == 4
        print(f"  -> Tên file đề xuất trên giao diện: {app.review.txt_proposed_filename.get()}")
        print(f"  -> HỘP: {app.review.txt_box.get()} | HỘP SỐ: {app.review.txt_box_number.get()}")
        print(f"  -> Nhận định: {app.review.opt_status_note.get()} | Dãy số: {app.review.txt_seq_summary.get()}")
        print(f"  -> Số dòng công dân trong bảng chỉnh sửa: {len(app.review.citizen_entries)} dòng.")

        # 6. Test Page Jump callback
        print("\n[6] Kiểm tra chức năng Click công dân để nhảy trang PDF...")
        app.review.on_page_jump_callback(2)
        assert app.viewer.current_page_idx == 1, "Viewer should jump to page index 1 (page 2)"
        print("  -> Nhảy trang thành công: Đang hiển thị trang", app.viewer.current_page_idx + 1)

        # 7. Test In-Place Confirmation Commit (Without deleting original file)
        print("\n[7] Kiểm tra nút Xác nhận: Lưu In-Place vào đúng thư mục tải lên...")
        app.review._handle_confirm()
        
        # Verify in-place files
        parent_dir = os.path.dirname(sample_pdf)
        new_pdf_path = os.path.join(parent_dir, f"{dossier_data['proposed_filename']}.pdf")
        new_xlsx_path = os.path.join(parent_dir, f"{dossier_data['proposed_filename']}.xlsx")
        
        assert os.path.exists(sample_pdf), "CRITICAL: Original PDF must NOT be deleted!"
        assert os.path.exists(new_pdf_path), "Renamed PDF must exist in the same upload folder!"
        assert os.path.exists(new_xlsx_path), "Companion XLSX must exist in the same upload folder!"
        
        print("  -> Kiểm tra tệp gốc: VẪN TỒN TẠI NGUYÊN VẸN TẠI:", sample_pdf)
        print("  -> Tệp PDF chuẩn mới được lưu tại:", new_pdf_path)
        print("  -> Tệp Excel tương ứng được lưu tại:", new_xlsx_path)

        # Check queue status updated
        item = app.sidebar.get_item(sample_pdf)
        assert item["status"] == "COMPLETED", f"Expected COMPLETED, got {item['status']}"
        print("  -> Trạng thái hàng đợi đã chuyển sang:", item["status"])

        print("\n" + "=" * 60)
        print(">>> KIỂM THỬ PHASE 2 HOÀN TẤT THÀNH CÔNG 100%! <<<")
        print("=" * 60)
        return True

    finally:
        app.destroy()

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
