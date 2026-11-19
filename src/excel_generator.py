"""
Module for generating standardized Excel companion files for digitized driving license registers.
"""
import os
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_excel_companion(
    dossier_meta: Dict[str, Any],
    citizens: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    Creates an Excel spreadsheet (.xlsx) mirroring the digitized PDF dossier.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách cấp GPLX"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_title = Font(name="Times New Roman", size=14, bold=True, color="002060")
    font_subtitle = Font(name="Times New Roman", size=11, italic=True)
    font_header = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Times New Roman", size=11)
    font_bold = Font(name="Times New Roman", size=11, bold=True)

    fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_alt = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )

    # 1. Document Title
    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value = "SỔ GỐC CẤP GIẤY PHÉP LÁI XE CƠ GIỚI ĐƯỜNG BỘ"
    title_cell.font = font_title
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # 2. Metadata info rows
    p_name = dossier_meta.get("province_name", "Yên Bái")
    p_code = dossier_meta.get("province_code", "15")
    hang = dossier_meta.get("license_class", "A1")
    khoa = dossier_meta.get("course", "25")
    ngay_thi = dossier_meta.get("exam_date", "")
    dia_diem = dossier_meta.get("exam_location", "")
    so_dau = dossier_meta.get("first_license_no", "")
    so_cuoi = dossier_meta.get("last_license_no", "")

    ws.merge_cells("A2:G2")
    ws["A2"].value = f"Đơn vị: SỞ GIAO THÔNG VẬN TẢI {p_name.upper()} (Mã tỉnh: {p_code}) | Hạng: {hang} | Khóa: {khoa}"
    ws["A2"].font = font_subtitle
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:G3")
    ws["A3"].value = f"Ngày thi: {ngay_thi} | Địa điểm: {dia_diem} | Dải số bằng: {so_dau} đến {so_cuoi}"
    ws["A3"].font = font_subtitle
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 20

    # 3. Table Column Headers
    headers = [
        ("STT", 6, "center"),
        ("Họ và tên", 26, "left"),
        ("Năm sinh", 12, "center"),
        ("Quốc tịch", 12, "center"),
        ("Nơi cư trú", 32, "left"),
        ("Số bằng", 16, "center"),
        ("Trang PDF", 12, "center")
    ]

    header_row = 5
    ws.row_dimensions[header_row].height = 24

    for col_idx, (col_name, col_width, col_align) in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = col_name
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    # 4. Populate Citizen Data
    current_row = header_row + 1
    for item in citizens:
        ws.row_dimensions[current_row].height = 20
        is_alt = (current_row % 2 == 1)

        row_data = [
            (item.get("stt", current_row - header_row), "center", font_body),
            (item.get("full_name", "").strip(), "left", font_bold),
            (item.get("birth_year", "").strip(), "center", font_body),
            (item.get("nationality", "Việt Nam").strip(), "center", font_body),
            (item.get("address", "").strip(), "left", font_body),
            (item.get("license_number", "").strip(), "center", font_bold),
            (item.get("page_number", 1), "center", font_body)
        ]

        for col_idx, (val, align, font_style) in enumerate(row_data, start=1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.value = val
            cell.font = font_style
            cell.alignment = Alignment(horizontal=align, vertical="center")
            cell.border = thin_border
            if is_alt:
                cell.fill = fill_alt

        current_row += 1

    # Save to disk
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb.save(output_path)
    return output_path
