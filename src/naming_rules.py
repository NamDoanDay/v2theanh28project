"""
Naming rules and filename validation module.
Specification:
- Pre-2012 Sổ quản lý (SQL): [Mã tỉnh].[SQL].[Tháng].[Năm].[Số bằng đầu]-[Số bằng cuối]
  Ví dụ: 15.SQL.03.1996.A161541-C244140
"""
import re
import os

FORBIDDEN_CHARS = re.compile(r'[\\/:*?"<>|]')

def clean_filename(filename: str) -> str:
    """Removes or replaces characters forbidden in Windows filenames."""
    return FORBIDDEN_CHARS.sub("-", filename).strip()

def normalize_license_code(raw_code: str) -> str:
    """
    Normalizes a license code:
    E.g.: 'A 161541' -> 'A161541'
          'c244138'  -> 'C244138'
          'A461S44-' -> 'A161541'
    """
    if not raw_code:
        return "UNKNOWN"
    
    cleaned = raw_code.strip().replace(" ", "").upper()
    # Strip any trailing or leading punctuation like '-', '.', ','
    cleaned = re.sub(r"^[^A-Z0-9]+|[^A-Z0-9]+$", "", cleaned)
    
    if not cleaned:
        return "UNKNOWN"

    # Identify prefix letters (1 or 2 letters)
    prefix_match = re.match(r"^([A-Z]{1,2})(.*)", cleaned)
    if prefix_match:
        prefix = prefix_match.group(1)
        suffix = prefix_match.group(2)
        
        # Convert common handwriting OCR errors in numeric suffix to digits:
        char_to_digit = {
            'S': '5', 's': '5',
            'O': '0', 'o': '0', 'D': '0', 'Q': '0',
            'I': '1', 'i': '1', 'L': '1', 'l': '1', '|': '1',
            'Z': '2', 'z': '2',
            'B': '8', 'b': '8',
            'G': '6'
        }
        converted_suffix = "".join([char_to_digit.get(ch, ch) for ch in suffix])
        # Keep only digits in suffix
        digits_only = re.sub(r"[^0-9]", "", converted_suffix)
        if digits_only:
            return f"{prefix}{digits_only}"
        return f"{prefix}{suffix}"

    return clean_filename(cleaned)

def build_dossier_filename(
    province_code: str,
    doc_type: str,
    month: str,
    year: str,
    first_license: str,
    last_license: str
) -> str:
    """
    Builds the standardized filename according to archival rules.
    Format: [Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối]
    Note: Uses '.' and '-' instead of '/' to ensure Windows file system compatibility.
    """
    p_code = str(province_code).strip().zfill(2)
    d_type = str(doc_type).strip().upper()
    
    # Clean month (e.g. '3' -> '03')
    m_clean = re.sub(r"[^0-9]", "", str(month))
    if m_clean:
        m_str = m_clean.zfill(2)
    else:
        m_str = "01"
        
    # Clean year (4 digits)
    y_clean = re.sub(r"[^0-9]", "", str(year))
    if len(y_clean) == 4:
        y_str = y_clean
    elif len(y_clean) == 2:
        y_str = f"19{y_clean}" if int(y_clean) > 50 else f"20{y_clean}"
    else:
        y_str = "1996"
        
    first_clean = normalize_license_code(first_license)
    last_clean = normalize_license_code(last_license)
    
    base_name = f"{p_code}.{d_type}.{m_str}.{y_str}.{first_clean}-{last_clean}"
    return clean_filename(base_name)
