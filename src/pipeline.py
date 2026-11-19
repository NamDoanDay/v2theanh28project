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
    
    return {
        "success": True,
        "pdf_path": target_pdf,
        "excel_path": target_xlsx,
        "master_summary_path": summary_path,
        "original_kept": original_pdf_path,
        "total_citizens": len(citizens),
        "final_filename": final_filename
    }
