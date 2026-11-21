"""
Module for managing and updating the Province Master Summary Excel file:
'SỔ THEO DÕI, RÀ SOÁT DÃY SỐ GPLX TRONG SỔ GỐC'
"""
import os
from contextlib import contextmanager
from datetime import datetime
from tempfile import mkstemp
from threading import RLock
from typing import Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HEADERS = [
    ("STT", 6, "center"),
    ("Loại sổ", 32, "left"),
    ("Ngày tại bìa sổ", 16, "center"),
    ("Tên file PDF", 36, "left"),
    ("HỘP", 10, "center"),
    ("HỘP SỐ", 12, "center"),
    ("Hạng", 10, "center"),
    ("Tổng số lượng GPLX", 18, "center"),
    ("Số GPLX trong file", 38, "left"),
    ("Tổng số trang PDF", 16, "center"),
    ("Ghi chú / nhận định", 24, "center"),
    ("Ngày cập nhật", 18, "center")
]

_SUMMARY_LOCK = RLock()
_RENAME_SHEET = "_GPLX_Rename"


def _new_summary_workbook():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Theo dõi dãy số GPLX"
    ws.views.sheetView[0].showGridLines = True

    # Title
    ws.merge_cells("A1:L1")
    title_cell = ws["A1"]
    title_cell.value = "SỔ THEO DÕI, RÀ SOÁT DÃY SỐ GPLX TRONG SỔ GỐC"
    title_cell.font = Font(name="Times New Roman", size=14, bold=True, color="002060")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Headers at row 2
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )

    ws.row_dimensions[2].height = 25
    for col_idx, (col_name, col_width, col_align) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=2, column=col_idx)
        cell.value = col_name
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    return wb


def _file_stamp(path):
    try:
        stat = os.stat(path)
        return stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return None


@contextmanager
def edit_master_summary(path):
    """Publish a complete workbook in one replacement so a locked file stays intact."""
    directory = os.path.dirname(os.path.abspath(path))
    with _SUMMARY_LOCK:
        stamp = _file_stamp(path)
        workbook = openpyxl.load_workbook(path) if stamp is not None else _new_summary_workbook()
        try:
            yield workbook
            os.makedirs(directory, exist_ok=True)
            fd, temporary = mkstemp(prefix=".gplx-", suffix=".xlsx", dir=directory)
            os.close(fd)
            try:
                workbook.save(temporary)
                if _file_stamp(path) != stamp:
                    raise OSError(f"Sổ tổng hợp đã thay đổi khi đang lưu: {os.path.basename(path)}. Hãy thử lại.")
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        finally:
            workbook.close()


def init_master_summary_file(file_path: str, province_name: str = "Tỉnh"):
    """Creates a new formatted Master Summary Excel file."""
    workbook = _new_summary_workbook()
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    workbook.save(file_path)
    return workbook


def _filename_key(name):
    return str(name or "").strip().casefold().removesuffix(".pdf")


def _summary_sheet(workbook):
    if "Theo dõi dãy số GPLX" in workbook.sheetnames:
        return workbook["Theo dõi dãy số GPLX"]
    return next(sheet for sheet in workbook.worksheets if sheet.sheet_state == "visible")


def summary_rows_by_name(workbook):
    worksheet = _summary_sheet(workbook)
    rows = {}
    if worksheet.max_row >= 3:
        for row, (value,) in enumerate(worksheet.iter_rows(min_row=3, min_col=4, max_col=4, values_only=True), 3):
            if key := _filename_key(value):
                rows.setdefault(key, []).append(row)
    return rows


def read_rename_records(workbook):
    if _RENAME_SHEET not in workbook.sheetnames:
        return []
    return [
        (filename, source, target)
        for filename, source, target in workbook[_RENAME_SHEET].iter_rows(min_row=2, max_col=3, values_only=True)
        if all(isinstance(value, str) and value for value in (filename, source, target))
    ]


def record_folder_rename(workbook, filename, source, target):
    """Validate ownership without relying on PDF bytes or the visible filename alone."""
    records = read_rename_records(workbook)
    wanted = _filename_key(filename)
    rows = summary_rows_by_name(workbook).get(wanted, [])
    source_key = os.path.normcase(os.path.normpath(source))
    target_key = os.path.normcase(os.path.normpath(target))
    owners = [(src, dest) for name, src, dest in records if _filename_key(name) == wanted]
    already_linked = len(owners) == 1 and len(rows) == 1 and (
        os.path.normcase(os.path.normpath(owners[0][0])), os.path.normcase(os.path.normpath(owners[0][1]))
    ) == (source_key, target_key)
    if already_linked:
        return True
    if owners or rows:
        raise FileExistsError(f"Sổ tổng hợp đã có tên {filename}.pdf cho hồ sơ khác hoặc chưa rõ nguồn. Hãy chọn tên khác.")
    if any(os.path.normcase(os.path.normpath(src)) == source_key for _, src, _ in records):
        raise FileExistsError("PDF nguồn đã được xác nhận với tên khác trong sổ tổng hợp.")
    if _RENAME_SHEET not in workbook.sheetnames:
        links = workbook.create_sheet(_RENAME_SHEET)
        links.sheet_state = "hidden"
        links.append(("Tên file", "PDF nguồn", "PDF đích"))
    links = workbook[_RENAME_SHEET]
    row = links.max_row + 1
    for index, value in enumerate((filename, source, target), 1):
        links.cell(row, index, value).data_type = "s"
    return False


def write_summary_entry(workbook, record: Dict[str, Any]) -> None:
    ws = _summary_sheet(workbook)
    
    # Styling
    font_body = Font(name="Times New Roman", size=11)
    font_bold = Font(name="Times New Roman", size=11, bold=True)
    fill_alt = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )

    pdf_filename = record.get("pdf_filename", "")
    
    rows = summary_rows_by_name(workbook).get(_filename_key(pdf_filename), [])
    target_row = rows[0] if rows else None
            
    is_new = (target_row is None)
    if is_new:
        target_row = ws.max_row + 1
        stt = target_row - 2
    else:
        stt = ws.cell(row=target_row, column=1).value or (target_row - 2)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    row_values = [
        (stt, "center", font_body),
        (record.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"), "left", font_body),
        (record.get("cover_date", ""), "center", font_body),
        (pdf_filename, "left", font_bold),
        (record.get("box", "48"), "center", font_body),
        (record.get("box_number", "115"), "center", font_body),
        (record.get("license_class", "A1"), "center", font_bold),
        (record.get("total_licenses", 0), "center", font_bold),
        (record.get("license_sequence", ""), "left", font_body),
        (record.get("total_pages", 1), "center", font_body),
        (record.get("status_note", "Đủ"), "center", font_bold),
        (now_str, "center", font_body)
    ]

    if is_new:
        ws.row_dimensions[target_row].height = 22
    for col_idx, (val, align, font_style) in enumerate(row_values, start=1):
        cell = ws.cell(row=target_row, column=col_idx)
        cell.value = val
        if isinstance(val, str):
            cell.data_type = "s"
        if is_new:
            cell.font = font_style
            cell.alignment = Alignment(horizontal=align, vertical="center")
            cell.border = thin_border
            if target_row % 2 == 1:
                cell.fill = fill_alt


def update_or_append_summary_entry(summary_file_path: str, record: Dict[str, Any]) -> str:
    with edit_master_summary(summary_file_path) as workbook:
        write_summary_entry(workbook, record)
    return summary_file_path
