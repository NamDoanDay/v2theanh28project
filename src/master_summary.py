"""
Module for managing and updating the Province Master Summary Excel file:
'SỔ THEO DÕI, RÀ SOÁT DÃY SỐ GPLX TRONG SỔ GỐC'
"""
import os
from datetime import datetime
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

def init_master_summary_file(file_path: str, province_name: str = "Tỉnh"):
    """Creates a new formatted Master Summary Excel file."""
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

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    wb.save(file_path)
    return wb

def update_or_append_summary_entry(summary_file_path: str, record: Dict[str, Any]) -> str:
    """
    Appends or updates a row for a digitized PDF dossier in the master summary workbook.
    """
    if not os.path.exists(summary_file_path):
        wb = init_master_summary_file(summary_file_path)
    else:
        wb = openpyxl.load_workbook(summary_file_path)
        
    ws = wb.active
    
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
    
    # Check if this PDF filename already exists in column 4 (Tên file PDF)
    target_row = None
    for r in range(3, ws.max_row + 1):
        cell_val = str(ws.cell(row=r, column=4).value or "").strip()
        if cell_val == pdf_filename:
            target_row = r
            break
            
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

    ws.row_dimensions[target_row].height = 22
    for col_idx, (val, align, font_style) in enumerate(row_values, start=1):
        cell = ws.cell(row=target_row, column=col_idx)
        cell.value = val
        cell.font = font_style
        cell.alignment = Alignment(horizontal=align, vertical="center")
        cell.border = thin_border
        if target_row % 2 == 1:
            cell.fill = fill_alt

    wb.save(summary_file_path)
    return summary_file_path
