"""
End-to-End Processing Pipeline for GPLX PDF dossiers.
Coordinates PDF rendering, OCR, parsing, naming, and Excel export.
"""
import os
import shutil
from copy import deepcopy
from filecmp import cmp
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Optional

import openpyxl
from src.pdf_processor import open_pdf, page_count, read_pdf_page_text, render_pdf_page
from src.ocr_engine import run_ocr
from src.cover_parser import parse_cover_ocr, parse_cover_page_text
from src.table_extractor import LicenseTableExtractor, measure_page_grid, table_citizens
from src.naming_rules import STANDARD_DOSSIER_PDF, is_valid_windows_filename_stem, propose_dossier_filename
from src.excel_generator import generate_excel_companion
from src.folder_parser import parse_folder_hierarchy, find_province_root_dir, folder_review_location
from src.sequence_analyzer import analyze_license_sequences
from src.master_summary import (
    edit_master_summary, read_rename_records, record_folder_rename, summary_rows_by_name,
    update_or_append_summary_entry, write_summary_entry,
)
from src.database import DatabaseManager
from src.config import PROVINCE_CODES
from src.logger import get_logger

logger = get_logger(__name__)


def _read_page_ocr(pdf, index):
    with render_pdf_page(pdf, index) as image:
        result, _ = run_ocr(image)
        return result, image.size


def _read_opening_page(pdf):
    from pypdfium2 import PdfiumError

    # A damaged or partial text layer is common in scanned decisions.
    try:
        text = read_pdf_page_text(pdf, 0)
    except PdfiumError:
        logger.warning("Could not read opening page text layer", exc_info=True)
        text = ""
    native = parse_cover_page_text(text)
    if native["document_type"] != "unknown" and not native["metadata_review"]:
        return native, None

    raw_ocr = _read_page_ocr(pdf, 0)
    scan = parse_cover_ocr(raw_ocr[0], raw_ocr[1][1])
    if native["document_type"] == "unknown":
        return scan, raw_ocr
    if native["document_type"] == scan["document_type"]:
        for field in ("province_code", "province_name", "exam_date", "decision_date", "decision_number",
                      "license_class", "course", "exam_location", "day", "month", "year"):
            if not native[field] and scan[field]:
                native[field] = scan[field]
                native["metadata_review"].pop(field, None)
                if field in scan["metadata_pages"]:
                    native["metadata_pages"][field] = scan["metadata_pages"][field]
    return native, raw_ocr


def _pdf_cache_key(pdf_path):
    path = os.path.realpath(pdf_path)
    stat = os.stat(path)
    return path, stat.st_size, stat.st_mtime_ns


@lru_cache(maxsize=8)
def _cached_opening(key):
    with open_pdf(key[0]) as pdf:
        total = page_count(pdf)
        if not total:
            raise ValueError("File PDF rỗng không có trang nào.")
        cover, opening_ocr = _read_opening_page(pdf)
        return cover, total, opening_ocr


@lru_cache(maxsize=4)
def _cached_tables(key):
    _, total, opening_ocr = _cached_opening(key)
    extractor = LicenseTableExtractor()
    with open_pdf(key[0]) as pdf:
        for index in range(total):
            logger.info("Reading GPLX table candidates on page %d/%d: %s", index + 1, total, key[0])
            with render_pdf_page(pdf, index) as image:
                result = opening_ocr[0] if index == 0 and opening_ocr is not None else run_ocr(image)[0]
                extractor.read_page(result, image.size, measure_page_grid(image), index + 1)
    return extractor.tables


def summarize_license_table(table):
    """Use the physical endpoints. Unknown cells and verified blanks have different results."""
    rows = table["rows"] if table else []
    unresolved = table.get("unresolved_pages", []) if table else []
    known_count = bool(rows) and not unresolved and all(row["identity_confident"] for row in rows)
    blank = bool(rows) and all(row["license_state"] == "blank" for row in rows)
    complete = known_count and all(row["license_state"] == "valid" for row in rows)
    sequence = analyze_license_sequences([row["license_number"] for row in rows] if complete else [])
    if not rows:
        warning = "Chưa xác định được danh sách GPLX."
    elif unresolved:
        warning = f"Cần đối chiếu trang {', '.join(map(str, unresolved))} để xác định danh sách có tiếp tục hay không."
    elif not known_count:
        warning = "Có dòng chưa đọc rõ họ tên. Hãy đối chiếu số lượng GPLX."
    elif blank:
        warning = "Cột số GPLX của danh sách đang trống."
    elif any(row["license_state"] == "unknown_column" for row in rows):
        warning = "Chưa xác định được cột số GPLX."
    elif not complete:
        warning = "Có ô số GPLX trống hoặc đọc chưa rõ. Hãy đối chiếu danh sách."
    else:
        warning = ""
    return {
        "first_license_no": rows[0]["license_number"] if rows else "",
        "last_license_no": rows[-1]["license_number"] if rows and not unresolved else "",
        "license_column_empty": blank and known_count,
        "license_sequence": sequence["sequence_summary"],
        "status_note": "Cần rà soát" if warning and not blank else sequence["status"],
        "total_licenses": len(rows) if known_count else None,
        "table_review": warning,
        "sequence_analysis": sequence,
    }


def process_dossier_pdf(pdf_path: str, default_province: str = "", *, rename_only: bool = False) -> Dict[str, Any]:
    """
    Processes a raw digitized PDF:
    1. Reads document metadata on the opening page
    2. Reads OCR and table data one page at a time
    4. Analyzes license sequences and continuity
    5. Extracts folder metadata (Hộp, Hộp số)
    6. Generates proposed standard filename
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    # 0. Extract folder hierarchy
    folder_info = folder_review_location(pdf_path) if rename_only else parse_folder_hierarchy(pdf_path)

    key = _pdf_cache_key(pdf_path)
    cached_cover, total_pages, _ = _cached_opening(key)
    cover_meta = deepcopy(cached_cover)
    tables = deepcopy(_cached_tables(key))
    all_citizens = [] if rename_only else [row for table in tables for row in table_citizens(table)]
    
    cover_meta["suggested_province_code"] = cover_meta["province_code"]
    cover_meta["province_code"] = default_province if default_province != "auto" else ""
    cover_meta["province_name"] = next(
        (p["name"] for p in PROVINCE_CODES if p["code"] == cover_meta["province_code"]), ""
    )

    # Attach folder metadata
    cover_meta["box"] = folder_info.get("box", "48")
    cover_meta["box_number"] = folder_info.get("box_number", "115")

    stats = summarize_license_table(tables[0] if len(tables) == 1 else None)
    seq_analysis = stats.pop("sequence_analysis")
    cover_meta.update(stats)
    if len(tables) > 1:
        cover_meta["table_review"] = "Có nhiều danh sách GPLX. Hãy chọn danh sách dùng để đặt tên."
    cover_meta["total_pages"] = total_pages

    # 5. Generate Standardized Filename
    proposal = propose_dossier_filename(
        province_code=cover_meta["province_code"],
        suggested_province_code=cover_meta["suggested_province_code"],
        exam_date=cover_meta["exam_date"],
        decision_number=cover_meta.get("decision_number", ""),
        decision_date=cover_meta.get("decision_date", ""),
        first_license_no=cover_meta["first_license_no"],
        last_license_no=cover_meta["last_license_no"],
        license_column_empty=cover_meta["license_column_empty"],
    )

    return {
        "original_path": pdf_path,
        "original_filename": os.path.basename(pdf_path),
        "proposed_filename": proposal.filename or "",
        "cover_meta": cover_meta,
        "citizens": all_citizens,
        "tables": tables,
        "total_citizens": len(all_citizens),
        "total_pages": total_pages,
        "sequence_analysis": seq_analysis,
        "folder_info": folder_info,
        "rename_only": rename_only,
        "source_stamp": key[1:],
        "status": "READY_FOR_REVIEW"
    }


def _copy_named_pdf(source, target, *, allow_existing=True):
    if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(target)):
        return False
    created = False
    try:
        with open(source, "rb") as original, open(target, "xb") as renamed:
            created = True
            shutil.copyfileobj(original, renamed)
        shutil.copystat(source, target)
        return True
    except FileExistsError:
        if not allow_existing or not cmp(source, target, shallow=False):
            raise FileExistsError(f"Đã có PDF mang tên {os.path.basename(target)}. Hãy kiểm tra hoặc chọn tên khác.")
        return False
    except OSError:
        if created:
            os.unlink(target)
        raise


_SUMMARY_PREFIX = "So_Theo_Doi_Day_So_GPLX_"


def list_folder_review_pdfs(folder_path):
    """List sources and registered results without queuing a renamed copy as a new PDF."""
    paths = sorted(
        (str(path.resolve()) for path in Path(folder_path).rglob("*") if path.suffix.lower() == ".pdf" and path.is_file()),
        key=str.casefold,
    )
    roots = {folder_review_location(path)["province_root"] for path in paths}
    registration = {}
    outputs = set()
    for root in roots:
        root_path = Path(root)
        for summary in root_path.glob(f"{_SUMMARY_PREFIX}[0-9][0-9].xlsx"):
            try:
                workbook = openpyxl.load_workbook(summary, read_only=True)
                try:
                    if not (records := read_rename_records(workbook)):
                        continue
                    names = summary_rows_by_name(workbook)
                    for filename, source, target in records:
                        if len(names.get(filename.strip().casefold().removesuffix(".pdf"), [])) != 1:
                            continue
                        original = (root_path / source).resolve()
                        renamed = (root_path / target).resolve()
                        if not original.is_relative_to(root_path) or not renamed.is_relative_to(root_path):
                            continue
                        if renamed.is_file():
                            source_key = os.path.normcase(str(original))
                            output_key = os.path.normcase(str(renamed))
                            registration[source_key] = str(renamed)
                            if source_key != output_key:
                                outputs.add(output_key)
                finally:
                    workbook.close()
            except Exception:
                logger.warning("Could not read registered folder PDFs from %s", summary, exc_info=True)
    return [(path, registration.get(os.path.normcase(path))) for path in dict.fromkeys(paths)
            if os.path.normcase(path) not in outputs]


def _summary_record(final_filename, cover_meta, total_citizens, *, folder_review=False):
    exam_date = cover_meta.get("exam_date", "")
    if folder_review and cover_meta.get("dossier_group") == "QĐTT":
        exam_date = cover_meta.get("decision_date", "")
    sequence = cover_meta.get("license_sequence", "")
    first = cover_meta.get("first_license_no")
    last = cover_meta.get("last_license_no")
    if not sequence and first and last and (folder_review or "license_sequence" not in cover_meta):
        sequence = f"Đầu {first} · Cuối {last}" if folder_review else f"{first}-{last}"
    return {
        "book_type": cover_meta.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"),
        "cover_date": exam_date,
        "pdf_filename": final_filename,
        "box": cover_meta.get("box", "48"),
        "box_number": cover_meta.get("box_number", "115"),
        "license_class": cover_meta.get("license_class", "A1"),
        "total_licenses": cover_meta.get("total_licenses", total_citizens),
        "license_sequence": sequence,
        "total_pages": cover_meta.get("total_pages", 1),
        "status_note": cover_meta.get("status_note", "Đủ"),
    }


def commit_folder_dossier(original_pdf_path, final_filename, cover_meta, *, source_stamp=None):
    """Publish the approved PDF and update its province workbook without exporting individual rows."""
    if not is_valid_windows_filename_stem(final_filename):
        raise ValueError("Tên file không hợp lệ cho Windows. Nhập tên và bỏ phần đuôi .pdf.")
    province = cover_meta.get("province_code")
    if province not in {p["code"] for p in PROVINCE_CODES}:
        raise ValueError("Hãy chọn mã tỉnh lưu trữ hợp lệ.")
    source, *current_stamp = _pdf_cache_key(original_pdf_path)
    if source_stamp is not None and tuple(current_stamp) != tuple(source_stamp):
        raise ValueError("PDF gốc đã thay đổi sau khi đọc. Hãy chọn lại thư mục để đọc PDF rồi xác nhận.")
    province_root = folder_review_location(source)["province_root"]
    target = os.path.join(os.path.dirname(source), f"{final_filename}.pdf")
    summary_path = os.path.join(province_root, f"{_SUMMARY_PREFIX}{province}.xlsx")

    copied = False
    try:
        logger.info("Folder review: checking archive name for %s -> %s", source, target)
        with edit_master_summary(summary_path) as workbook:
            linked = record_folder_rename(
                workbook, final_filename, os.path.relpath(source, province_root), os.path.relpath(target, province_root),
            )
            copied = _copy_named_pdf(source, target, allow_existing=linked)
            logger.info("Folder review: updating summary %s for %s", summary_path, source)
            write_summary_entry(workbook, _summary_record(final_filename, cover_meta, None, folder_review=True))
    except Exception as exc:
        if copied:
            try:
                if os.path.exists(target):
                    if not cmp(source, target, shallow=False):
                        raise OSError("PDF đích đã bị thay đổi trong lúc lưu.")
                    os.unlink(target)
                    logger.info("Folder review: rolled back new PDF %s", target)
            except OSError:
                logger.exception("Folder review: could not remove incomplete output %s", target)
                raise OSError(f"Chưa lưu được sổ tổng hợp và không thể thu hồi bản sao {os.path.basename(target)}. "
                              "Hãy đóng PDF đích, chuyển bản sao sang vị trí khác rồi thử lại.") from exc
        if isinstance(exc, PermissionError):
            raise PermissionError(f"Không ghi được PDF hoặc sổ {os.path.basename(summary_path)}. "
                                  "Hãy đóng sổ trong Excel và kiểm tra quyền ghi rồi thử lại.") from exc
        raise
    logger.info("Folder review: saved PDF and summary for %s", source)
    return {"pdf_path": target, "master_summary_path": summary_path}


def commit_dossier(
    original_pdf_path: str,
    final_filename: str,
    cover_meta: Dict[str, Any],
    citizens: List[Dict[str, Any]],
    output_dir: Optional[str] = None,
    *,
    source_tables=None,
    source_stamp=None,
) -> Dict[str, Any]:
    """
    Executes the rename, companion Excel generation, and updates Master Summary:
    1. Saves new renamed PDF directly into output_dir (defaults to same folder as uploaded file)
       WITHOUT deleting or modifying the original file.
    2. Generates companion Excel in the same folder.
    3. Updates Province Master Summary Excel: So_Theo_Doi_Day_So_GPLX_<prov>.xlsx at Province root folder.
    """
    if not is_valid_windows_filename_stem(final_filename):
        raise ValueError("Tên file không hợp lệ cho Windows. Nhập tên và bỏ phần đuôi .pdf.")
    if source_stamp is not None and _pdf_cache_key(original_pdf_path)[1:] != tuple(source_stamp):
        raise ValueError("PDF gốc đã thay đổi sau khi đọc. Hãy đọc lại hồ sơ trước khi xuất Excel.")

    # If output_dir is not specified, save in-place directly in the uploaded file's folder
    if not output_dir:
        output_dir = os.path.dirname(os.path.abspath(original_pdf_path))

    os.makedirs(output_dir, exist_ok=True)
    
    target_pdf = os.path.join(output_dir, f"{final_filename}.pdf")
    target_xlsx = os.path.join(output_dir, f"{final_filename}.xlsx")
    
    # Safe copy without deleting original file
    copied = _copy_named_pdf(original_pdf_path, target_pdf)
    
    try:
        generate_excel_companion(cover_meta, citizens, target_xlsx, source_tables=source_tables, pdf_path=target_pdf)
    except Exception:
        if copied:
            try:
                os.unlink(target_pdf)
            except OSError:
                logger.exception("Could not clean up PDF after Excel export failed: %s", target_pdf)
        raise

    # Master summary update: place at province root folder
    prov_code = cover_meta.get("province_code", "15")
    prov_root = find_province_root_dir(original_pdf_path)
    summary_filename = f"{_SUMMARY_PREFIX}{prov_code}.xlsx"
    summary_path = os.path.join(prov_root, summary_filename)

    update_or_append_summary_entry(summary_path, _summary_record(final_filename, cover_meta, len(citizens)))

    # 4. Zero-Config Database Sync into SQLite
    db_error = None
    try:
        db = DatabaseManager()
        db.insert_or_update_dossier(
            final_filename=final_filename,
            cover_meta=cover_meta,
            citizens=citizens,
            pdf_path=target_pdf,
            excel_path=target_xlsx
        )
    except Exception as exc:
        logger.exception("SQLite sync failed for %s", final_filename)
        db_error = str(exc)
    
    return {
        "success": True,
        "pdf_path": target_pdf,
        "excel_path": target_xlsx,
        "master_summary_path": summary_path,
        "original_kept": original_pdf_path,
        "total_citizens": len(citizens),
        "db_error": db_error,
        "final_filename": final_filename
    }

def fast_extract_rename_metadata(pdf_path: str, default_province: str = "") -> str:
    """Read the header first. SQL names also need the endpoints of a unique GPLX list."""
    logger.info("Folder rename: opening PDF %s", pdf_path)
    key = _pdf_cache_key(pdf_path)
    cover_meta, total_pages, _ = _cached_opening(key)
    logger.info("Folder rename: PDF has %d pages, type=%s, review_fields=%s: %s",
                total_pages, cover_meta["document_type"], list(cover_meta["metadata_review"]), pdf_path)
    fields = {
        "province_code": default_province,
        "suggested_province_code": cover_meta["province_code"],
        "exam_date": cover_meta["exam_date"],
        "decision_number": cover_meta["decision_number"],
        "decision_date": cover_meta["decision_date"],
    }
    proposal = propose_dossier_filename(**fields)
    if proposal.filename:
        return proposal.filename
    if proposal.group != "SQL" or proposal.errors.keys() - {"first_license_no", "last_license_no"}:
        raise ValueError("Cần rà soát: " + " ".join(proposal.errors.values()))

    tables = _cached_tables(key)
    if len(tables) != 1:
        reason = "Có nhiều danh sách GPLX. Hãy chọn danh sách trong màn hình duyệt." if tables else "Chưa tìm thấy danh sách GPLX."
        raise ValueError("Cần rà soát: " + reason)
    stats = summarize_license_table(tables[0])
    proposal = propose_dossier_filename(
        **fields,
        first_license_no=stats["first_license_no"],
        last_license_no=stats["last_license_no"],
        license_column_empty=stats["license_column_empty"],
    )
    if proposal.filename is None:
        raise ValueError("Cần rà soát: " + " ".join(proposal.errors.values()))
    return proposal.filename

def batch_copy_and_rename_folder_pdfs(
    folder_path: str,
    default_province: str = "",
    progress_callback = None
) -> Dict[str, Any]:
    """
    Scans a folder for raw PDFs and copies files with sufficient OCR data under their proposed names.
    Preserves 100% of original files without modifying them. Does not generate companion Excel files.
    """
    import time

    logger.info("Folder rename started: folder=%s province=%s", folder_path, default_province)

    found_pdfs = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(".pdf") and not STANDARD_DOSSIER_PDF.fullmatch(f):
                found_pdfs.append(os.path.join(root, f))
    found_pdfs.sort()

    total_files = len(found_pdfs)
    results = []
    logger.info("Folder rename found %d unrenamed PDF files in %s", total_files, folder_path)

    for idx, pdf_path in enumerate(found_pdfs, start=1):
        started_at = time.monotonic()
        try:
            logger.info(
                "Folder rename file %d/%d started: path=%s size_bytes=%d",
                idx, total_files, pdf_path, os.path.getsize(pdf_path),
            )
            if progress_callback:
                progress_callback(idx, total_files, os.path.basename(pdf_path))

            # Thuật toán đọc nhanh siêu tốc: Chỉ đọc Trang 1, Trang 2 và Trang cuối
            new_filename = fast_extract_rename_metadata(pdf_path, default_province=default_province)

            parent_dir = os.path.dirname(os.path.abspath(pdf_path))
            new_pdf_path = os.path.join(parent_dir, f"{new_filename}.pdf")

            # Copy to new file, keeping original intact
            _copy_named_pdf(pdf_path, new_pdf_path)

            results.append({
                "original_path": pdf_path,
                "new_path": new_pdf_path,
                "new_filename": new_filename,
                "success": True,
                "error": None
            })
            logger.info(
                "Folder rename file %d/%d completed: output=%s elapsed_seconds=%.1f",
                idx, total_files, new_pdf_path, time.monotonic() - started_at,
            )
        except Exception as e:
            logger.exception(
                "Folder rename file %d/%d failed after %.1f seconds: %s",
                idx, total_files, time.monotonic() - started_at, pdf_path,
            )
            results.append({
                "original_path": pdf_path,
                "new_path": None,
                "new_filename": None,
                "success": False,
                "error": str(e)
            })

    result = {
        "total_scanned": total_files,
        "success_count": sum(1 for r in results if r["success"]),
        "failed_count": sum(1 for r in results if not r["success"]),
        "results": results
    }
    logger.info(
        "Folder rename finished: folder=%s total=%d success=%d failed=%d",
        folder_path, result["total_scanned"], result["success_count"], result["failed_count"],
    )
    return result
