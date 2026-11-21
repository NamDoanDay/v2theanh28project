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
import unicodedata
from pathlib import Path
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

def _is_system_or_user_root(path_obj: Path) -> bool:
    """Check if path is a top-level user directory like Desktop, Documents, or drive root."""
    resolved = path_obj.resolve()
    home = Path.home().resolve()
    if resolved == home or resolved in home.parents or len(resolved.parts) <= 2:
        return True
    # Check common user directories: Desktop, Downloads, Documents, etc.
    if resolved.parent == home and resolved.name.lower() in {
        "desktop", "documents", "downloads", "pictures", "videos", "music"
    }:
        return True
    return False


def find_province_root_dir(pdf_path: str) -> str:
    """
    Finds the province root folder in the path hierarchy:
    E.g. D:/Data/LaoCai/HOP_48/HOP_SO_115/scan.pdf -> D:/Data/LaoCai
    If path is less than 3 levels deep or parent is a system folder, returns the immediate directory of the PDF.
    """
    abs_dir = os.path.dirname(os.path.abspath(pdf_path))
    parts = abs_dir.replace("\\", "/").split("/")
    
    if len(parts) >= 3:
        prov_dir = os.path.abspath(os.path.join(abs_dir, "..", ".."))
        if os.path.exists(prov_dir) and not _is_system_or_user_root(Path(prov_dir)):
            return prov_dir

    return abs_dir


def folder_review_location(pdf_path: str) -> Dict[str, str]:
    """Find the province and box fields for folders selected at any archive level."""
    parent = Path(pdf_path).resolve().parent
    lineage = [*reversed(parent.parents), parent]
    root = parent
    archive_province = None
    box = box_number = ""
    for index, folder in enumerate(lineage):
        key = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", folder.name.casefold()))
        if key in {"dulieusohoagpls", "dulieusohoagplx", "dulieugplx"} and index + 1 < len(lineage):
            next_folder = lineage[index + 1]
            if re.fullmatch(r"0[123]_.*", next_folder.name) and index + 2 < len(lineage):
                next_folder = lineage[index + 2]
            root = archive_province = next_folder
        elif re.fullmatch(r"(?:hopso|hoso)(?:\d+|[a-z][a-z0-9]*)", key):
            box_number = extract_clean_number_or_name(folder.name)
            if not box and root == parent and not _is_system_or_user_root(folder.parent):
                root = folder.parent
        elif not box and re.fullmatch(r"(?:hop|tu)\d+", key):
            if not archive_province or archive_province == folder:
                if not _is_system_or_user_root(folder.parent):
                    root = folder.parent
                else:
                    root = folder
            box = extract_clean_number_or_name(folder.name)
    if _is_system_or_user_root(root):
        root = parent
    return {"province_root": str(root), "province_folder": root.name, "box": box, "box_number": box_number}
