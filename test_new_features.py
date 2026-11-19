"""
Automated Test for New Features:
1. Batch Folder PDF Copy & Rename (`batch_copy_and_rename_folder_pdfs`)
2. Dossier & Excel Inventory Tracking (`get_all_dossiers`, `get_inventory_stats`, drill-down)
"""
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager
from src.pipeline import batch_copy_and_rename_folder_pdfs

def test_inventory_features():
    print("=" * 65)
    print("KIỂM THỬ TÍNH NĂNG 1: THEO DÕI HỒ SƠ / FILE EXCEL ĐÃ IMPORT")
    print("=" * 65)

    db = DatabaseManager()

    # 1. Inventory stats
    stats = db.get_inventory_stats()
    print("[1] Thống kê toàn diện (Inventory Stats):")
    print(f"  -> Tổng số tỉnh: {stats['total_provinces']}")
    print(f"  -> Tổng số Hộp (Tủ): {stats['total_boxes']}")
    print(f"  -> Tổng số Hộp số (Hồ sơ): {stats['total_box_numbers']}")
    print(f"  -> Tổng số Cuốn sổ / File Excel: {stats['total_dossiers']}")
    print(f"  -> Tổng số GPLX: {stats['total_citizens']}")
    assert stats['total_dossiers'] > 0, "Lỗi: Không tìm thấy cuốn sổ nào trong CSDL"

    # 2. Get all dossiers
    dossiers = db.get_all_dossiers(province_code="all", box="all")
    print(f"\n[2] Lấy danh sách toàn bộ hồ sơ trong CSDL (tìm thấy {len(dossiers)} cuốn sổ):")
    assert len(dossiers) > 0
    first_d = dossiers[0]
    print(f"  -> Sổ #1: {first_d['final_filename']}")
    print(f"     Mã tỉnh: {first_d['province_code']} | HỘP: {first_d['box']} | HỘP SỐ: {first_d['box_number']}")
    print(f"     Số lượng bằng: {first_d['total_citizens']} | Dãy số: {first_d['license_sequence']} | Nhận định: {first_d['status_note']}")
    assert first_d['final_filename'], "Tên file không được rỗng"

    # 3. Test filter by box
    distinct_boxes = db.get_distinct_boxes()
    print(f"\n[3] Danh sách các Hộp phân cấp: {distinct_boxes}")
    if distinct_boxes:
        filtered_by_box = db.get_all_dossiers(box=distinct_boxes[0])
        print(f"  -> Lọc theo Hộp '{distinct_boxes[0]}': {len(filtered_by_box)} cuốn sổ.")
        assert len(filtered_by_box) > 0

    # 4. Test drill-down to citizens in dossier
    target_dossier_id = first_d['id']
    citizens_in_dossier = db.search(query="", dossier_id=target_dossier_id)
    print(f"\n[4] Kiểm tra Drill-Down (Xem toàn bộ công dân trong sổ #{target_dossier_id}):")
    print(f"  -> Tìm thấy: {len(citizens_in_dossier)} công dân.")
    assert len(citizens_in_dossier) == first_d['total_citizens']
    for c in citizens_in_dossier:
        print(f"     [STT {c['stt']}] {c['full_name']} | Bằng: {c['license_number']} | Năm sinh: {c['birth_year']}")

    print("\n>>> TÍNH NĂNG THEO DÕI HỒ SƠ ĐÃ IMPORT ĐẠT 100% PASS! <<<")


def test_batch_rename_folder_features():
    print("\n" + "=" * 65)
    print("KIỂM THỬ TÍNH NĂNG 2: ĐỔI TÊN FILE (THEO FOLDER)")
    print("=" * 65)

    # Prepare temp folder with a sample raw PDF
    temp_dir = tempfile.mkdtemp(prefix="gplx_batch_test_")
    sample_src = os.path.join(os.path.dirname(__file__), "samples", "LaoCai", "HOP_48", "HOP_SO_115", "sample_input.pdf")
    if not os.path.exists(sample_src):
        sample_src = os.path.join(os.path.dirname(__file__), "samples", "sample_input.pdf")

    temp_raw_pdf = os.path.join(temp_dir, "raw_unrenamed_document.pdf")
    shutil.copy2(sample_src, temp_raw_pdf)

    print(f"[1] Tạo thư mục kiểm thử tạm thời:")
    print(f"  -> Thư mục: {temp_dir}")
    print(f"  -> File PDF gốc: {os.path.basename(temp_raw_pdf)}")

    progress_log = []
    def on_progress(cur, total, fn):
        progress_log.append((cur, total, fn))
        print(f"  [Tiến trình {cur}/{total}] Đang xử lý: {fn}")

    # Run batch copy and rename
    print(f"\n[2] Thực thi batch_copy_and_rename_folder_pdfs...")
    res = batch_copy_and_rename_folder_pdfs(temp_dir, default_province="15", progress_callback=on_progress)

    print(f"\n[3] Kết quả đổi tên theo folder:")
    print(f"  -> Tổng file quét: {res['total_scanned']}")
    print(f"  -> Thành công: {res['success_count']}")
    print(f"  -> Thất bại: {res['failed_count']}")
    assert res['total_scanned'] == 1
    assert res['success_count'] == 1

    first_res = res['results'][0]
    expected_new_path = first_res['new_path']
    print(f"  -> File mới tạo: {os.path.basename(expected_new_path)}")

    # Verify original file is PRESERVED 100%
    print(f"\n[4] Kiểm tra tính toàn vẹn:")
    print(f"  -> File PDF gốc CÒN TỒN TẠI NGUYÊN VẸN: {os.path.exists(temp_raw_pdf)}")
    assert os.path.exists(temp_raw_pdf), "Lỗi: File gốc bị mất hoặc bị xóa!"

    # Verify new file exists
    print(f"  -> File PDF mới đổi tên TỒN TẠI: {os.path.exists(expected_new_path)}")
    assert os.path.exists(expected_new_path), "Lỗi: File mới không được tạo!"
    assert expected_new_path.endswith(".pdf")

    # Verify NO companion Excel was generated for this feature
    excel_counterpart = expected_new_path.replace(".pdf", ".xlsx")
    print(f"  -> Kiểm tra không tạo file Excel thừa: {not os.path.exists(excel_counterpart)}")
    assert not os.path.exists(excel_counterpart), "Lỗi: Chức năng này không được tạo file Excel!"

    # Clean up temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n>>> TÍNH NĂNG ĐỔI TÊN FILE THEO FOLDER ĐẠT 100% PASS! <<<")


if __name__ == "__main__":
    test_inventory_features()
    test_batch_rename_folder_features()
    print("\n" + "=" * 65)
    print(">>> TOÀN BỘ KIỂM THỬ TÍNH NĂNG MỚI ĐẠT 100% PASS! <<<")
    print("=" * 65)
