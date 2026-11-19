"""
Verification Script for Phase 3: Zero-Config SQLite Database, FTS5 Search & Jump to Page.
"""
import os
import sys

# Ensure src is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager, remove_vietnamese_accents
from src.pipeline import process_dossier_pdf, commit_dossier

def run_test():
    print("=" * 60)
    print("BẮT ĐẦU KIỂM THỬ PHASE 3: CSDL ZERO-CONFIG & TRA CỨU NHẢY TRANG")
    print("=" * 60)

    db = DatabaseManager()
    print("[1] Khởi tạo CSDL SQLite thành công tại:", db.db_path)

    sample_pdf = os.path.join(os.path.dirname(__file__), "samples", "LaoCai", "HOP_48", "HOP_SO_115", "sample_input.pdf")
    if not os.path.exists(sample_pdf):
        sample_pdf = os.path.join(os.path.dirname(__file__), "samples", "sample_input.pdf")

    # 1. Process & Commit Dossier to populate DB
    print(f"\n[2] Nạp và xử lý tệp mẫu: {sample_pdf}")
    dossier_data = process_dossier_pdf(sample_pdf, default_province="15")
    
    parent_dir = os.path.dirname(sample_pdf)
    commit_res = commit_dossier(
        original_pdf_path=sample_pdf,
        final_filename=dossier_data["proposed_filename"],
        cover_meta=dossier_data["cover_meta"],
        citizens=dossier_data["citizens"],
        output_dir=parent_dir
    )
    print(f"  -> Đã lưu và đồng bộ vào SQLite: {commit_res['total_citizens']} công dân.")

    # 2. Check Database Stats
    stats = db.get_stats()
    print(f"\n[3] Thống kê CSDL hiện tại: {stats['total_citizens']} công dân, {stats['total_dossiers']} cuốn sổ.")
    assert stats["total_citizens"] >= 4, "Must have at least 4 citizens indexed"

    # 3. Test Search by Exact and Partial License Number
    print("\n[4] Kiểm tra Tìm kiếm theo Số Bằng Lái Xe:")
    res_lic1 = db.search("A461544")
    print(f"  + Tìm 'A461544': tìm thấy {len(res_lic1)} kết quả.")
    assert len(res_lic1) > 0, "Must find citizen with license A461544"
    print(f"    -> Tên: {res_lic1[0]['full_name']} | Bằng: {res_lic1[0]['license_number']} | Trang PDF: {res_lic1[0]['page_number']}")

    res_lic2 = db.search("C244138")
    print(f"  + Tìm 'C244138': tìm thấy {len(res_lic2)} kết quả.")
    assert len(res_lic2) > 0
    print(f"    -> Tên: {res_lic2[0]['full_name']} | Bằng: {res_lic2[0]['license_number']} | Trang PDF: {res_lic2[0]['page_number']}")

    # 4. Test Search by Accented and Unaccented Name
    print("\n[5] Kiểm tra Tìm kiếm theo Họ và Tên (Tiếng Việt có dấu & không dấu):")
    res_name_unacc = db.search("tran van yen")
    print(f"  + Tìm không dấu 'tran van yen': tìm thấy {len(res_name_unacc)} kết quả.")
    assert len(res_name_unacc) > 0, "Must find Tran Van Yen with unaccented search"

    res_name_acc = db.search("Thúy")
    print(f"  + Tìm có dấu 'Thúy': tìm thấy {len(res_name_acc)} kết quả.")
    assert len(res_name_acc) > 0, "Must find Nguyen Van Thuy"
    print(f"    -> Khớp tên: {res_name_acc[0]['full_name']} (Năm sinh {res_name_acc[0]['birth_year']})")

    # 5. Test Search by Birth Year
    print("\n[6] Kiểm tra Tìm kiếm theo Năm Sinh:")
    res_year = db.search("1965")
    print(f"  + Tìm năm sinh '1965': tìm thấy {len(res_year)} kết quả.")
    assert len(res_year) > 0
    print(f"    -> Khớp: {res_year[0]['full_name']} | Số bằng: {res_year[0]['license_number']}")

    # 6. Test Jump-to-Page Metadata Integrity
    print("\n[7] Kiểm tra Tính Toàn Vẹn Đường Dẫn & Số Trang Nhảy Tới:")
    first_hit = res_lic1[0]
    assert os.path.exists(first_hit["pdf_path"]), f"PDF file must exist at {first_hit['pdf_path']}"
    assert os.path.exists(first_hit["excel_path"]), f"Excel file must exist at {first_hit['excel_path']}"
    assert first_hit["page_number"] == 2, "Page number must be 2"
    print(f"  -> File PDF: {first_hit['pdf_path']}")
    print(f"  -> File Excel: {first_hit['excel_path']}")
    print(f"  -> Nhảy đến chính xác Trang: {first_hit['page_number']}")
    print(f"  -> Vị trí hồ sơ: HỘP {first_hit['box']} - HỘP SỐ {first_hit['box_number']}")

    # 7. Test Re-indexing from directory
    print("\n[8] Kiểm tra Tính Năng Quét Lại Từ Excel (Re-indexing):")
    reindexed = db.reindex_from_directory(parent_dir)
    print(f"  -> Đã quét và đồng bộ lại: {reindexed} cuốn sổ từ thư mục.")
    assert reindexed >= 1, "Must reindex at least 1 book"

    print("\n" + "=" * 60)
    print(">>> KIỂM THỬ PHASE 3 HOÀN TẤT THÀNH CÔNG 100%! <<<")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
