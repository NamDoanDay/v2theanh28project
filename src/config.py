"""
Configuration and constants for GPLX Digitization and Renaming System.
"""
import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROVINCE_CODES_FILE = os.path.join(DATA_DIR, "province_codes.json")

# Default folders
DEFAULT_INPUT_DIR = os.path.join(BASE_DIR, "DuLieu_GPLX", "01_ChuaXuLy")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "DuLieu_GPLX", "02_DaXuLy_HoanThanh")
DEFAULT_ERROR_DIR = os.path.join(BASE_DIR, "DuLieu_GPLX", "03_CoLoi_CanXemLai")
DATABASE_PATH = os.path.join(BASE_DIR, "HeThong", "gplx_index.db")

# Regex pattern for License Numbers:
# Historical licenses usually start with 1-2 letters (A, B, C, AM,...) followed by 5-7 digits
# E.g. A161541, C244138, AM570000, A466375, C244132
LICENSE_PATTERN = re.compile(r"([A-Za-z]{1,2})\s*([0-9]{5,7})")

def load_province_codes():
    if os.path.exists(PROVINCE_CODES_FILE):
        with open(PROVINCE_CODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

PROVINCE_CODES = load_province_codes()

def find_province_code_by_text(text: str) -> str:
    """
    Search for matching province name or keywords from extracted text.
    Returns 2-digit code (e.g. '15') or None.
    """
    if not text:
        return "15" # Default fallback
    
    text_lower = text.lower()
    for prov in PROVINCE_CODES:
        for kw in prov.get("keywords", []):
            if kw in text_lower:
                return prov["code"]
    return "15"
