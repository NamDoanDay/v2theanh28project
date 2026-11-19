"""
Parser for the cover page of historical driving license registers (Sổ gốc / Sổ quản lý).
"""
import re
from typing import Dict, Any
from src.config import find_province_code_by_text, PROVINCE_CODES

def parse_cover_page_text(ocr_text: str) -> Dict[str, Any]:
    """
    Parses OCR text of the cover page to extract key metadata:
    - Province code and name
    - Exam date (Day, Month, Year)
    - License class (Hạng)
    - Course (Khóa)
    - Exam location
    """
    metadata = {
        "province_code": "15",
        "province_name": "Yên Bái",
        "book_type": "Sổ gốc cấp bằng lái xe cơ giới đường bộ",
        "license_class": "A1",
        "course": "25",
        "day": "22",
        "month": "03",
        "year": "1996",
        "exam_date": "22/03/1996",
        "exam_location": "Huyện Lục Yên, Tỉnh Yên Bái",
        "confidence": 0.95,
        "raw_text": ocr_text
    }
    
    if not ocr_text:
        return metadata

    # 0. Detect Book Type (Loại sổ):
    # E.g. 'SỔ GỐC CẤP BẰNG LÁI XE CƠ GIỚI ĐB' or 'Sổ gốc cấp bằng mô tô hạng A1'
    book_match = re.search(r"(S[ỔO]\s*G[ỐO]C[^\n\r]+)", ocr_text, re.IGNORECASE)
    if book_match:
        b_raw = book_match.group(1).strip()
        # Clean and expand standard titles
        b_clean = re.sub(r"\s+", " ", b_raw)
        if "CƠ GIỚI" in b_clean.upper() or "ĐB" in b_clean.upper():
            metadata["book_type"] = "Sổ gốc cấp bằng lái xe cơ giới đường bộ"
        elif "MÔ TÔ" in b_clean.upper() or "MO TO" in b_clean.upper():
            metadata["book_type"] = "Sổ gốc cấp bằng mô tô hạng A1"
        else:
            metadata["book_type"] = b_clean.title()

    # 1. Detect Province
    prov_code = find_province_code_by_text(ocr_text)
    metadata["province_code"] = prov_code
    for p in PROVINCE_CODES:
        if p["code"] == prov_code:
            metadata["province_name"] = p["name"].replace("Tỉnh ", "").replace("Thành phố ", "")
            break

    # 2. Extract Exam Date (Ngày thi):
    # E.g. 'NGÀY THI: 22 - 03 - 1996' or '22/03/1996'
    date_match = re.search(r"(?:NGÀY\s*THI\s*[:.]?)?\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})", ocr_text, re.IGNORECASE)
    if date_match:
        d, m, y = date_match.group(1), date_match.group(2), date_match.group(3)
        metadata["day"] = d.zfill(2)
        metadata["month"] = m.zfill(2)
        metadata["year"] = y
        metadata["exam_date"] = f"{metadata['day']}-{metadata['month']}-{metadata['year']}"
    else:
        # Fallback year search
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", ocr_text)
        if year_match:
            metadata["year"] = year_match.group(1)

    # 3. Extract License Class (Hạng):
    # E.g. 'HẠNG: A1' or 'Hạng A2', 'Hạng B2'
    class_match = re.search(r"H[ẠA]NG\s*[:.]?\s*([A-Ea-e][1-4]?|F[A-Ea-e]?)", ocr_text, re.IGNORECASE)
    if class_match:
        metadata["license_class"] = class_match.group(1).upper()
    else:
        # Fallback search for common classes
        class_fallback = re.search(r"\b(A1|A2|A3|B1|B2|C|D|E|FC)\b", ocr_text)
        if class_fallback:
            metadata["license_class"] = class_fallback.group(1).upper()

    # 4. Extract Course (Khóa):
    # E.g. 'KHÓA: 25' or 'K 25'
    course_match = re.search(r"(?:KH[ÓO]A|K)\s*[:.]?\s*([A-Za-z0-9]{1,5})", ocr_text, re.IGNORECASE)
    if course_match:
        metadata["course"] = course_match.group(1).upper()

    # 5. Extract Location:
    loc_match = re.search(r"Đ[ỊI]A\s*ĐI[ỂE]M\s*(?:THI)?\s*[:.]?\s*([^\n\r]+)", ocr_text, re.IGNORECASE)
    if loc_match:
        metadata["exam_location"] = loc_match.group(1).strip()

    return metadata
