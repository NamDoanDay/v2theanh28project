"""
End-to-End Processing Pipeline for GPLX PDF dossiers.
Coordinates PDF rendering, OCR, parsing, naming, and Excel export.
"""
import os
import shutil
from typing import Dict, Any, List
from src.pdf_processor import render_pdf_to_images
from src.ocr_engine import run_ocr
from src.cover_parser import parse_cover_page_text
from src.table_extractor import cluster_boxes_into_rows
from src.naming_rules import build_dossier_filename
from src.excel_generator import generate_excel_companion
from src.folder_parser import parse_folder_hierarchy, find_province_root_dir
from src.sequence_analyzer import analyze_license_sequences
from src.master_summary import update_or_append_summary_entry
from src.database import DatabaseManager
from src.config import DEFAULT_OUTPUT_DIR

def process_dossier_pdf(pdf_path: str, default_province: str = "15") -> Dict[str, Any]:
    """
    Processes a raw digitized PDF:
    1. Extracts images
    2. Runs OCR on Cover page (page 1)
    3. Runs OCR and table extraction on subsequent pages
    4. Analyzes license sequences and continuity
    5. Extracts folder metadata (Hộp, Hộp số)
    6. Generates proposed standard filename
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    # 0. Extract folder hierarchy
    folder_info = parse_folder_hierarchy(pdf_path)

    # 1. Render pages
    pages = render_pdf_to_images(pdf_path, dpi=200)
    total_pages = len(pages)
    if total_pages == 0:
        raise ValueError("PDF file is empty")

    # 2. Process Page 1: Cover Page
    cover_img = pages[0]
    cover_ocr_res, cover_time = run_ocr(cover_img)
    cover_text = " ".join([str(item[1]) for item in cover_ocr_res])
    cover_meta = parse_cover_page_text(cover_text)
    
    if default_province and default_province != "auto":
        cover_meta["province_code"] = default_province

    # Attach folder metadata
    cover_meta["box"] = folder_info.get("box", "48")
    cover_meta["box_number"] = folder_info.get("box_number", "115")

    # 3. Process Table Pages (Page 2 to Page N)
    all_citizens: List[Dict[str, Any]] = []
    
    table_pages = pages[1:] if total_pages > 1 else pages
    start_page_num = 2 if total_pages > 1 else 1

    for idx, page_img in enumerate(table_pages):
        page_num = start_page_num + idx
        w, h = page_img.size
        tbl_ocr_res, tbl_time = run_ocr(page_img)
        page_citizens = cluster_boxes_into_rows(tbl_ocr_res, w, h)
        for c in page_citizens:
            c["page_number"] = page_num
        all_citizens.extend(page_citizens)

    # Đánh số thứ tự STT lần lượt liên tục từ 1 đến N cho toàn bộ danh sách trong file
    for idx, c in enumerate(all_citizens, start=1):
        c["stt"] = idx

    # 4. Analyze License Sequences and Continuity
    license_list = [c.get("license_number", "") for c in all_citizens if c.get("license_number")]
    seq_analysis = analyze_license_sequences(license_list)

    first_license = "A000000"
    last_license = "C999999"
    
    if license_list:
        first_license = license_list[0]
        last_license = license_list[-1]

    cover_meta["first_license_no"] = first_license
    cover_meta["last_license_no"] = last_license
    cover_meta["license_sequence"] = seq_analysis["sequence_summary"]
    cover_meta["status_note"] = seq_analysis["status"]
    cover_meta["total_licenses"] = len(all_citizens)
    cover_meta["total_pages"] = total_pages

    # 5. Generate Standardized Filename
    proposed_name = build_dossier_filename(
        province_code=cover_meta.get("province_code", "15"),
        doc_type="SQL",
        month=cover_meta.get("month", "03"),
        year=cover_meta.get("year", "1996"),
        first_license=first_license,
        last_license=last_license
    )

    return {
        "original_path": pdf_path,
        "original_filename": os.path.basename(pdf_path),
        "proposed_filename": proposed_name,
        "cover_meta": cover_meta,
        "citizens": all_citizens,
        "total_citizens": len(all_citizens),
        "total_pages": total_pages,
        "sequence_analysis": seq_analysis,
        "folder_info": folder_info,
        "status": "READY_FOR_REVIEW"
    }

def commit_dossier(
    original_pdf_path: str,
    final_filename: str,
    cover_meta: Dict[str, Any],
    citizens: List[Dict[str, Any]],
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the rename, companion Excel generation, and updates Master Summary:
    1. Saves new renamed PDF directly into output_dir (defaults to same folder as uploaded file)
       WITHOUT deleting or modifying the original file.
    2. Generates companion Excel in the same folder.
    3. Updates Province Master Summary Excel: So_Theo_Doi_Day_So_GPLX_<prov>.xlsx at Province root folder.
    """
    # If output_dir is not specified, save in-place directly in the uploaded file's folder
    if not output_dir:
        output_dir = os.path.dirname(os.path.abspath(original_pdf_path))

    os.makedirs(output_dir, exist_ok=True)
    
    target_pdf = os.path.join(output_dir, f"{final_filename}.pdf")
    target_xlsx = os.path.join(output_dir, f"{final_filename}.xlsx")
    
    # Safe copy without deleting original file
    if os.path.abspath(original_pdf_path) != os.path.abspath(target_pdf):
        shutil.copy2(original_pdf_path, target_pdf)
    
    # Generate matching Excel companion
    generate_excel_companion(cover_meta, citizens, target_xlsx)

    # Master summary update: place at province root folder
    prov_code = cover_meta.get("province_code", "15")
    prov_root = find_province_root_dir(original_pdf_path)
    summary_filename = f"So_Theo_Doi_Day_So_GPLX_{prov_code}.xlsx"
    summary_path = os.path.join(prov_root, summary_filename)

    summary_record = {
        "book_type": cover_meta.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"),
        "cover_date": cover_meta.get("exam_date", ""),
        "pdf_filename": final_filename,
        "box": cover_meta.get("box", "48"),
        "box_number": cover_meta.get("box_number", "115"),
        "license_class": cover_meta.get("license_class", "A1"),
        "total_licenses": len(citizens),
        "license_sequence": cover_meta.get("license_sequence", f"{cover_meta.get('first_license_no')}-{cover_meta.get('last_license_no')}"),
        "total_pages": cover_meta.get("total_pages", 1),
        "status_note": cover_meta.get("status_note", "Đủ")
    }

    update_or_append_summary_entry(summary_path, summary_record)

    # 4. Zero-Config Database Sync into SQLite
    try:
        db = DatabaseManager()
        db.insert_or_update_dossier(
            final_filename=final_filename,
            cover_meta=cover_meta,
            citizens=citizens,
            pdf_path=target_pdf,
            excel_path=target_xlsx
        )
    except Exception as e:
        print(f"Warning: SQLite sync failed: {e}")
    
    return {
        "success": True,
        "pdf_path": target_pdf,
        "excel_path": target_xlsx,
        "master_summary_path": summary_path,
        "original_kept": original_pdf_path,
        "total_citizens": len(citizens),
        "final_filename": final_filename
    }

def fast_extract_rename_metadata(pdf_path: str, default_province: str = "15") -> str:
    """
    Thuật toán trích xuất siêu tốc tối ưu riêng cho chức năng đổi tên file (theo folder):
    - Đọc Trang 1 (Bìa) để lấy Mã tỉnh, Tháng, Năm của ngày thi/ngày ký sổ.
    - Đọc Trang 2 (Trang danh sách đầu tiên) tại Hàng 1 để lấy Số bằng đầu (STT 1).
    - Đọc Trang cuối (Trang danh sách cuối) tại Hàng cuối để lấy Số bằng cuối (STT cuối).
    - BỎ QUA HOÀN TOÀN TẤT CẢ CÁC TRANG Ở GIỮA (tiết kiệm 90% thời gian xử lý và CPU).
    - Nếu ô đầu/cuối bị mờ/trống: Tự động quét dòng kế cận gần nhất để đảm bảo luôn lấy được số bằng chuẩn.
    """
    import re
    from src.pdf_processor import get_pdf_page_count, render_specific_pdf_pages
    from src.naming_rules import normalize_license_code

    total_pages = get_pdf_page_count(pdf_path)
    if total_pages == 0:
        raise ValueError("File PDF rỗng không có trang nào.")

    # Chỉ render tối đa 3 trang cần thiết
    if total_pages == 1:
        needed_indices = [0]
    elif total_pages == 2:
        needed_indices = [0, 1]
    else:
        needed_indices = [0, 1, total_pages - 1]

    rendered_pages = render_specific_pdf_pages(pdf_path, needed_indices, dpi=200)

    # 1. Đọc Trang bìa (Trang 1 - index 0)
    cover_img = rendered_pages[0]
    cover_ocr_res, _ = run_ocr(cover_img)
    cover_text = " ".join([str(item[1]) for item in cover_ocr_res])
    cover_meta = parse_cover_page_text(cover_text)

    folder_info = parse_folder_hierarchy(pdf_path)
    prov_code = cover_meta.get("province_code") or folder_info.get("province_code") or default_province or "15"

    exam_date = cover_meta.get("exam_date", "")
    month, year = "01", "1996"
    if exam_date and "-" in exam_date:
        parts = exam_date.split("-")
        if len(parts) >= 3:
            month = parts[1].strip()
            year = parts[2].strip()
        elif len(parts) == 2:
            month = parts[0].strip()
            year = parts[1].strip()
    else:
        m_date = re.search(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})", cover_text)
        if m_date:
            month = m_date.group(2)
            year = m_date.group(3)
        else:
            m_my = re.search(r"(\d{1,2})[\/\-\.](\d{4})", cover_text)
            if m_my:
                month = m_my.group(1)
                year = m_my.group(2)

    def extract_license_from_page(img, direction="first"):
        w, h = img.size
        ocr_res, _ = run_ocr(img)
        rows = cluster_boxes_into_rows(ocr_res, w, h)
        if direction == "last":
            rows = list(reversed(rows))

        # Quét lần lượt các dòng (dòng 1 trước, nếu mờ thì quét dòng kế cận)
        for r in rows:
            lic = r.get("license_number", "")
            if lic and lic != "UNKNOWN" and len(lic) >= 5:
                return lic

        # Cứu nguy: Quét toàn bộ các box text trên trang
        box_texts = [str(item[1]).strip() for item in ocr_res]
        if direction == "last":
            box_texts = list(reversed(box_texts))

        for text in box_texts:
            m = re.search(r"([A-Za-z]{1,2}\s*[0-9]{5,7})", text)
            if m:
                return normalize_license_code(m.group(1))

        return None

    # 2. Đọc Trang 2 (Trang danh sách đầu tiên) -> Số bằng đầu
    first_license = "A000000"
    if total_pages >= 2:
        p2_img = rendered_pages[1]
        found = extract_license_from_page(p2_img, direction="first")
        if found:
            first_license = found
    else:
        found = extract_license_from_page(cover_img, direction="first")
        if found:
            first_license = found

    # 3. Đọc Trang cuối -> Số bằng cuối
    last_license = first_license
    if total_pages >= 3:
        last_idx = total_pages - 1
        last_img = rendered_pages[last_idx]
        found = extract_license_from_page(last_img, direction="last")
        if found:
            last_license = found
    elif total_pages == 2:
        p2_img = rendered_pages[1]
        found = extract_license_from_page(p2_img, direction="last")
        if found:
            last_license = found

    return build_dossier_filename(
        province_code=prov_code,
        doc_type="SQL",
        month=month,
        year=year,
        first_license=first_license,
        last_license=last_license
    )

def batch_copy_and_rename_folder_pdfs(
    folder_path: str,
    default_province: str = "15",
    progress_callback = None
) -> Dict[str, Any]:
    """
    Scans a folder for raw scanned PDF files, extracts metadata and license ranges via OCR,
    and copies each file into a new file named [Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf.
    Preserves 100% of original files without modifying them. Does not generate companion Excel files.
    """
    import shutil
    import re

    # Pattern identifying files that are already renamed according to standard format
    STANDARD_PATTERN = re.compile(r"^\d{2}\.SQL\.\d{2}\.\d{4}\..*\.pdf$", re.IGNORECASE)

    found_pdfs = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(".pdf") and not STANDARD_PATTERN.match(f):
                found_pdfs.append(os.path.join(root, f))

    total_files = len(found_pdfs)
    results = []

    for idx, pdf_path in enumerate(found_pdfs, start=1):
        if progress_callback:
            progress_callback(idx, total_files, os.path.basename(pdf_path))

        try:
            # Thuật toán đọc nhanh siêu tốc: Chỉ đọc Trang 1, Trang 2 và Trang cuối
            new_filename = fast_extract_rename_metadata(pdf_path, default_province=default_province)

            parent_dir = os.path.dirname(os.path.abspath(pdf_path))
            new_pdf_path = os.path.join(parent_dir, f"{new_filename}.pdf")

            # Copy to new file, keeping original intact
            if os.path.abspath(pdf_path) != os.path.abspath(new_pdf_path):
                shutil.copy2(pdf_path, new_pdf_path)

            results.append({
                "original_path": pdf_path,
                "new_path": new_pdf_path,
                "new_filename": new_filename,
                "success": True,
                "error": None
            })
        except Exception as e:
            results.append({
                "original_path": pdf_path,
                "new_path": None,
                "new_filename": None,
                "success": False,
                "error": str(e)
            })

    return {
        "total_scanned": total_files,
        "success_count": sum(1 for r in results if r["success"]),
        "failed_count": sum(1 for r in results if not r["success"]),
        "results": results
    }
