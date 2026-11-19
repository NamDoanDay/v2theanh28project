"""
Parser for folder path hierarchy:
Format: [Tỉnh] / [Hộp / Tủ hồ sơ] / [Hộp số / Hộp giấy] / [file.pdf]
E.g.: DuLieu_GPLX/LaoCai/HOP_48/HOP_SO_115/scan_001.pdf
      -> Tỉnh: LaoCai
      -> Hộp: 48
      -> Hộp số: 115
"""
import os
import re
from typing import Dict, Any

def extract_clean_number_or_name(folder_name: str) -> str:
    """
    Extracts number if present (e.g. 'HOP_48' -> '48', 'Hop so 115' -> '115'),
    otherwise returns clean uppercase string.
    """
    if not folder_name:
        return ""
        
    cleaned = folder_name.strip()
    # Try extracting digits
    digits = re.findall(r"\d+", cleaned)
    if digits:
        return digits[-1] # Usually the number at the end: HOP 48 -> 48
        
    # Remove common prefix words: HOP, TU, HO SO, HOP SO
    name = re.sub(r"(?i)^(HỘP|HOP|TỦ|TU|HỒ SƠ|HO SO|HỘP SỐ|HOP SO)[\s_\-]*", "", cleaned)
    return name.strip() or cleaned

def parse_folder_hierarchy(pdf_path: str) -> Dict[str, str]:
    """
    Parses full or relative file path to determine Box (Hộp) and Box Number (Hộp số).
    """
    abs_path = os.path.abspath(pdf_path)
    parts = abs_path.replace("\\", "/").split("/")
    
    # Defaults
    info = {
        "province_folder": "",
        "box": "48",       # HỘP (Tủ hồ sơ)
        "box_number": "115" # HỘP SỐ (Hộp giấy)
    }
    
    if len(parts) >= 2:
        # Parent folder of the PDF is typically Hộp số (Hop so 115, Ho so 115)
        box_num_raw = parts[-2]
        info["box_number"] = extract_clean_number_or_name(box_num_raw)
        
    if len(parts) >= 3:
        # Grandparent folder is typically Hộp (HOP 48, Tu 48)
        box_raw = parts[-3]
        info["box"] = extract_clean_number_or_name(box_raw)
        
    if len(parts) >= 4:
        info["province_folder"] = parts[-4]
        
    return info

def find_province_root_dir(pdf_path: str) -> str:
    """
    Finds the province root folder in the path hierarchy:
    E.g. D:/Data/LaoCai/HOP_48/HOP_SO_115/scan.pdf -> D:/Data/LaoCai
    If path is less than 3 levels deep, returns the immediate directory of the PDF.
    """
    abs_dir = os.path.dirname(os.path.abspath(pdf_path))
    parts = abs_dir.replace("\\", "/").split("/")
    
    # Check if grandparent is Hộp and great-grandparent is Province
    if len(parts) >= 3:
        # Check if parent folder looks like Hộp số / Ho so
        # and grandparent looks like Hộp / Tu
        # Then province root is 2 levels above:
        prov_dir = os.path.abspath(os.path.join(abs_dir, "..", ".."))
        if os.path.exists(prov_dir):
            return prov_dir

    return abs_dir
