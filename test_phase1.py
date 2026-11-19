"""
Verification and Test script for Phase 1: Core Engine & OCR Pipeline.
"""
import os
import sys

# Ensure src is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import process_dossier_pdf, commit_dossier
from src.config import DEFAULT_OUTPUT_DIR

def run_test():
    sample_pdf = os.path.join(os.path.dirname(__file__), "samples", "LaoCai", "HOP_48", "HOP_SO_115", "sample_input.pdf")
    if not os.path.exists(sample_pdf):
        sample_pdf = os.path.join(os.path.dirname(__file__), "samples", "sample_input.pdf")
        
    print("=" * 60)
    print("BẮT ĐẦU KIỂM THỬ PHASE 1: CORE OCR ENGINE, AUTO-RENAME & MASTER SUMMARY")
    print("=" * 60)
    print(f"[1] Nạp tệp mẫu PDF từ cấu trúc thư mục:\n    {sample_pdf}")

    try:
        # Step 1: Process PDF
        print("[2] Đang chạy OCR & Trích xuất cấu trúc Bìa + Bảng danh sách...")
        result = process_dossier_pdf(sample_pdf, default_province="15")
        
        print("\n--- KẾT QUẢ TRÍCH XUẤT THÔNG TIN TRANG BÌA & THƯ MỤC ---")
        cover = result["cover_meta"]
        print(f"  + Loại sổ: {cover.get('book_type')}")
        print(f"  + Mã tỉnh: {cover.get('province_code')} ({cover.get('province_name')})")
        print(f"  + HỘP (Tủ hồ sơ): {cover.get('box')}")
        print(f"  + HỘP SỐ (Hộp giấy): {cover.get('box_number')}")
        print(f"  + Hạng GPLX: {cover.get('license_class')}")
        print(f"  + Khóa thi: {cover.get('course')}")
        print(f"  + Ngày tại bìa sổ: {cover.get('exam_date')}")
        print(f"  + Tổng số trang PDF: {result.get('total_pages')}")
        print(f"  + Tổng số lượng GPLX: {result.get('total_citizens')}")
        print(f"  + Rà soát dãy số GPLX: {cover.get('license_sequence')}")
        print(f"  + Ghi chú / nhận định: {cover.get('status_note')}")
        
        print("\n--- DANH SÁCH CÔNG DÂN TRÍCH XUẤT ĐƯỢC TỪ BẢNG ---")
        citizens = result["citizens"]
        for c in citizens:
            print(f"  [STT {c.get('stt')}] {c.get('full_name'):<22} | Năm sinh: {c.get('birth_year'):<4} | Nơi cư trú: {c.get('address'):<24} | Số bằng: {c.get('license_number')}")
            
        print("\n--- QUY TẮC ĐẶT TÊN FILE TỰ ĐỘNG ---")
        print(f"  + Số bằng đầu (STT 1): {cover.get('first_license_no')}")
        print(f"  + Số bằng cuối: {cover.get('last_license_no')}")
        print(f"  + Tên file đề xuất: {result['proposed_filename']}")
        
        # Step 2: Commit and generate Excel
        print("\n[3] Thực hiện Đổi tên PDF, Tạo tệp Excel đồng hành & Cập nhật Sổ Theo Dõi Tỉnh...")
        commit_res = commit_dossier(
            original_pdf_path=sample_pdf,
            final_filename=result["proposed_filename"],
            cover_meta=cover,
            citizens=citizens,
            output_dir=DEFAULT_OUTPUT_DIR
        )
        
        print(f"  + Tệp PDF chuẩn đã lưu:      {commit_res['pdf_path']}")
        print(f"  + Tệp Excel tương ứng:        {commit_res['excel_path']}")
        print(f"  + File Excel Tổng Hợp Tỉnh:   {commit_res['master_summary_path']}")
        print(f"  + Kiểm tra tồn tại PDF:       {os.path.exists(commit_res['pdf_path'])}")
        print(f"  + Kiểm tra tồn tại XLSX:      {os.path.exists(commit_res['excel_path'])}")
        print(f"  + Kiểm tra tồn tại Tổng Hợp:  {os.path.exists(commit_res['master_summary_path'])}")
        
        print("\n" + "=" * 60)
        print(">>> KIỂM THỬ PHASE 1 HOÀN TẤT THÀNH CÔNG RỰC RỠ! <<<")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[LỖI] Có lỗi xảy ra trong quá trình xử lý: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
