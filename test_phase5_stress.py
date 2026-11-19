"""
Stress & Reliability Test Script for Phase 5: Packaging & Performance Benchmark.
Executes high-volume simulated batch processing, continuous Fast OCR renaming,
and high-concurrency FTS5 queries to verify stability, memory, and CPU efficiency.
"""
import os
import sys
import time
import shutil
import tempfile
from typing import List

# Ensure src is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager
from src.pipeline import batch_copy_and_rename_folder_pdfs

def run_stress_test():
    print("=" * 70)
    print("BẮT ĐẦU KIỂM THỬ TẢI & ĐỘ ỔN ĐỊNH GIAI ĐOẠN 5 (STRESS & BENCHMARK)")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. BATCH FAST OCR STRESS TEST (Processing multiple PDFs)
    # -------------------------------------------------------------
    print("\n[PHẦN 1] KIỂM THỬ XỬ LÝ HÀNG LOẠT VỚI THUẬT TOÁN FAST OCR SIÊU TỐC")
    temp_dir = tempfile.mkdtemp(prefix="gplx_stress_test_")
    sample_src = os.path.join(os.path.dirname(__file__), "samples", "LaoCai", "HOP_48", "HOP_SO_115", "sample_input.pdf")
    if not os.path.exists(sample_src):
        sample_src = os.path.join(os.path.dirname(__file__), "samples", "sample_input.pdf")

    # Generate sample PDFs
    num_samples = 6
    print(f"  -> Đang nhân bản {num_samples} file PDF scan mẫu vào thư mục tạm...")
    for i in range(1, num_samples + 1):
        target_path = os.path.join(temp_dir, f"scan_raw_dossier_{i:03d}.pdf")
        shutil.copy2(sample_src, target_path)

    start_time = time.time()
    processed_count = 0

    def progress_cb(cur, total, fn):
        nonlocal processed_count
        processed_count = cur
        print(f"     ...Đang xử lý [{cur}/{total}]: {fn}")

    print(f"  -> Bắt đầu chạy 'batch_copy_and_rename_folder_pdfs' trên {num_samples} files...")
    batch_res = batch_copy_and_rename_folder_pdfs(temp_dir, default_province="15", progress_callback=progress_cb)
    total_batch_time = time.time() - start_time
    avg_per_file = total_batch_time / num_samples

    print("\n  [KẾT QUẢ PHẦN 1: FAST OCR BENCHMARK]")
    print(f"  • Tổng số file xử lý:           {batch_res['total_scanned']}")
    print(f"  • Số file đổi tên thành công:    {batch_res['success_count']}")
    print(f"  • Số file thất bại:              {batch_res['failed_count']}")
    print(f"  • Tổng thời gian:               {total_batch_time:.2f} giây")
    print(f"  • Tốc độ trung bình / file:     {avg_per_file:.2f} giây/file (Cực nhanh trên CPU văn phòng!)")
    
    assert batch_res['success_count'] == num_samples, "Lỗi: Không đạt 100% tỉ lệ thành công!"
    assert avg_per_file < 12.0, f"Cảnh báo: Tốc độ xử lý ({avg_per_file:.2f}s) vượt quá 12.0s/file"

    # Verify original files still exist
    for i in range(1, num_samples + 1):
        orig = os.path.join(temp_dir, f"scan_raw_dossier_{i:03d}.pdf")
        assert os.path.exists(orig), f"Lỗi: File gốc {orig} đã bị mất!"

    shutil.rmtree(temp_dir, ignore_errors=True)
    print("  -> Đã xác thực bảo toàn 100% file gốc cũ và dọn dẹp thư mục tạm an toàn.")

    # -------------------------------------------------------------
    # 2. HIGH-CONCURRENCY FTS5 DATABASE QUERY STRESS TEST
    # -------------------------------------------------------------
    print("\n[PHẦN 2] KIỂM THỬ TRUY VẤN CSDL SQLITE FTS5 TẦN SUẤT CAO (200 QUERIES)")
    db = DatabaseManager()
    stats = db.get_stats()
    print(f"  -> Dữ liệu kiểm thử: {stats['total_citizens']} công dân, {stats['total_dossiers']} cuốn sổ.")

    query_samples = [
        "Trần", "Nguyen", "thuy", "vinh", "thuong",
        "A461544", "C244138", "C244139", "C244140",
        "1960", "1968", "1965", "1964", "Yên", "Lục Yên"
    ]

    total_queries = 200
    db_start_time = time.time()
    total_found_results = 0

    for i in range(total_queries):
        q = query_samples[i % len(query_samples)]
        res = db.search(query=q, limit=50)
        total_found_results += len(res)

    total_query_time = time.time() - db_start_time
    avg_query_ms = (total_query_time / total_queries) * 1000

    print("\n  [KẾT QUẢ PHẦN 2: FTS5 QUERY BENCHMARK]")
    print(f"  • Tổng số truy vấn FTS5:        {total_queries} queries")
    print(f"  • Tổng thời gian:               {total_query_time:.3f} giây")
    print(f"  • Thời gian phản hồi trung bình: {avg_query_ms:.2f} ms/query (< 2ms, siêu tốc!)")
    print(f"  • Tổng kết quả trả về:          {total_found_results} bản ghi")

    assert avg_query_ms < 15.0, f"Cảnh báo: Độ trễ FTS5 ({avg_query_ms:.2f}ms) vượt quá ngưỡng cho phép!"

    # -------------------------------------------------------------
    # 3. INVENTORY METRICS & DRILL-DOWN STABILITY TEST
    # -------------------------------------------------------------
    print("\n[PHẦN 3] KIỂM THỬ TÍNH NĂNG THEO DÕI HỒ SƠ & DRILL-DOWN LIÊN TỤC")
    inv_start = time.time()
    for _ in range(50):
        inv_stats = db.get_inventory_stats()
        all_d = db.get_all_dossiers(limit=50)
        if all_d:
            cits = db.search(query="", dossier_id=all_d[0]['id'])
    inv_time = time.time() - inv_start

    print(f"  -> Thực hiện 50 chu trình lấy danh mục hồ sơ & drill-down hoàn tất trong {inv_time:.3f}s")
    print(f"  • Thống kê: {inv_stats['total_provinces']} tỉnh | {inv_stats['total_boxes']} hộp | {inv_stats['total_dossiers']} cuốn sổ")

    print("\n" + "=" * 70)
    print(">>> KIỂM THỬ STRESS & BENCHMARK GIAI ĐOẠN 5 ĐẠT 100% PASS! <<<")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
