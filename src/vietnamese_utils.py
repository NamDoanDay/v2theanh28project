"""
Vietnamese Diacritics Restoration & Normalization Utility.
Accurately restores accents for Vietnamese Names, Administrative Addresses, and Common Words.
"""
import re
from typing import Dict, List

# Dictionary of Common Vietnamese Surnames (Họ)
VIETNAMESE_SURNAMES: Dict[str, str] = {
    "tran": "Trần", "nguyen": "Nguyễn", "le": "Lê", "pham": "Phạm",
    "hoang": "Hoàng", "huynh": "Huỳnh", "phan": "Phan", "vu": "Vũ",
    "vo": "Võ", "dang": "Đặng", "bui": "Bùi", "do": "Đỗ", "bo": "Đỗ",
    "ho": "Hồ", "ngo": "Ngô", "duong": "Dương", "ly": "Lý",
    "dao": "Đào", "doan": "Đoàn", "dinh": "Đinh", "lam": "Lâm",
    "phung": "Phùng", "mai": "Mai", "trinh": "Trịnh", "luong": "Lương",
    "luu": "Lưu", "ha": "Hà", "cao": "Cao", "thai": "Thái",
    "ta": "Tạ", "tong": "Tống", "truong": "Trương", "quach": "Quách",
    "chu": "Chu", "chau": "Châu", "nghiem": "Nghiêm", "tu": "Từ"
}

# Common Vietnamese Middle Names (Tên đệm)
VIETNAMESE_MIDDLE_NAMES: Dict[str, str] = {
    "van": "Văn", "thi": "Thị", "tien": "Tiến", "duc": "Đức",
    "huu": "Hữu", "dinh": "Đình", "xuan": "Xuân", "vi": "Vi",
    "ngoc": "Ngọc", "thanh": "Thanh", "quang": "Quang", "minh": "Minh",
    "cong": "Công", "duy": "Duy", "anh": "Anh", "bao": "Bảo",
    "hai": "Hải", "tuan": "Tuấn", "kim": "Kim", "hong": "Hồng",
    "trong": "Trọng", "ba": "Bá", "phuoc": "Phước", "dai": "Đại",
    "the": "Thế", "phu": "Phú", "chi": "Chí", "manh": "Mạnh"
}

# Common Vietnamese Given Names (Tên gọi)
VIETNAMESE_GIVEN_NAMES: Dict[str, str] = {
    "yen": "Yên", "thuy": "Thúy", "vinh": "Vinh", "thuong": "Thượng",
    "thutdng": "Thượng", "thuong'": "Thượng", "hung": "Hùng", "dung": "Dũng",
    "tuan": "Tuấn", "nam": "Nam", "binh": "Bình", "lan": "Lan",
    "hoa": "Hoa", "mai": "Mai", "huong": "Hương", "linh": "Linh",
    "phuong": "Phương", "cuong": "Cường", "thang": "Thắng", "hai": "Hải",
    "hieu": "Hiếu", "dat": "Đạt", "huy": "Huy", "tung": "Tùng",
    "long": "Long", "khoa": "Khoa", "trung": "Trung", "phuc": "Phúc",
    "kien": "Kiên", "quan": "Quân", "son": "Sơn", "ha": "Hà",
    "toan": "Toàn", "truong": "Trường", "giang": "Giang", "diep": "Diệp",
    "thao": "Thảo", "trang": "Trang", "nga": "Nga", "hang": "Hằng",
    "tuyet": "Tuyết", "nguyet": "Nguyệt", "quyen": "Quyên", "anh": "Anh",
    "chien": "Chiến", "loi": "Lợi", "loc": "Lộc", "phat": "Phát",
    "tai": "Tài", "nghia": "Nghĩa", "thuan": "Thuận", "khanh": "Khánh",
    "phong": "Phong", "vuong": "Vương", "canh": "Cảnh", "thanh": "Thành"
}

# Administrative Gazetteer (Địa danh hành chính)
ADMIN_LOCATIONS: Dict[str, str] = {
    "yen bai": "Yên Bái", "luc yen": "Lục Yên", "van chan": "Văn Chấn",
    "van yen": "Văn Yên", "tran yen": "Trấn Yên", "tram tau": "Trạm Tấu",
    "mu cang chai": "Mù Cang Chải", "nghia lo": "Nghĩa Lộ",
    "lao cai": "Lào Cai", "bao thang": "Bảo Thắng", "bao yen": "Bảo Yên",
    "bat xat": "Bát Xát", "bac ha": "Bắc Hà", "sa pa": "Sa Pa",
    "si ma cai": "Si Ma Cai", "muong khuong": "Mường Khương",
    "tuyen quang": "Tuyên Quang", "phu tho": "Phú Thọ", "ha noi": "Hà Nội",
    "viet nam": "Việt Nam", "iviet nam": "Việt Nam"
}

def restore_vietnamese_name(raw_name: str) -> str:
    """
    Restores Vietnamese accents for personal names.
    E.g. 'Tran Van Yen'    -> 'Trần Văn Yên'
         'Nguyen Van Thuy' -> 'Nguyễn Văn Thúy'
         'Hoang Tien Vinh' -> 'Hoàng Tiến Vinh'
         'Bo Vi Thutdng'   -> 'Đỗ Vi Thượng'
    """
    if not raw_name:
        return ""
        
    cleaned = raw_name.strip()
    words = cleaned.split()
    if not words:
        return ""

    restored_words = []
    num_words = len(words)

    for idx, w in enumerate(words):
        w_clean = re.sub(r"[^A-Za-z0-9àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]", "", w)
        w_lower = w_clean.lower()

        # If word already has accents, preserve it capitalized
        if re.search(r"[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]", w_clean):
            restored_words.append(w_clean.capitalize())
            continue

        # Rule 1: First word is typically Surname
        if idx == 0 and w_lower in VIETNAMESE_SURNAMES:
            restored_words.append(VIETNAMESE_SURNAMES[w_lower])
        # Rule 2: Last word is typically Given Name
        elif idx == num_words - 1 and w_lower in VIETNAMESE_GIVEN_NAMES:
            restored_words.append(VIETNAMESE_GIVEN_NAMES[w_lower])
        # Rule 3: Middle words
        elif w_lower in VIETNAMESE_MIDDLE_NAMES:
            restored_words.append(VIETNAMESE_MIDDLE_NAMES[w_lower])
        elif w_lower in VIETNAMESE_GIVEN_NAMES:
            restored_words.append(VIETNAMESE_GIVEN_NAMES[w_lower])
        elif w_lower in VIETNAMESE_SURNAMES:
            restored_words.append(VIETNAMESE_SURNAMES[w_lower])
        else:
            # Fallback capitalize
            restored_words.append(w_clean.capitalize())

    return " ".join(restored_words)

def normalize_vietnamese_address(raw_addr: str) -> str:
    """
    Restores accents and standardizes Vietnamese administrative addresses.
    E.g. 'H.Luc yen tinh Yen bai' -> 'H. Lục Yên, Tỉnh Yên Bái'
    """
    if not raw_addr:
        return ""
        
    addr = raw_addr.strip()
    addr_lower = addr.lower()

    # Normalize common abbreviations
    addr = re.sub(r"(?i)\bh\.\s*", "H. ", addr)
    addr = re.sub(r"(?i)\btp\.\s*", "TP. ", addr)
    addr = re.sub(r"(?i)\btx\.\s*", "TX. ", addr)
    addr = re.sub(r"(?i)\btinh\s+", "Tỉnh ", addr)
    addr = re.sub(r"(?i)\bhuyen\s+", "Huyện ", addr)

    # Replace known administrative names with accented versions
    for key, val in ADMIN_LOCATIONS.items():
        pattern = re.compile(re.escape(key), re.IGNORECASE)
        addr = pattern.sub(val, addr)

    # Clean spacing and punctuation
    addr = re.sub(r"\s+", " ", addr)
    if "Tỉnh" in addr and not addr.startswith("Tỉnh") and ", Tỉnh" not in addr:
        addr = addr.replace(" Tỉnh", ", Tỉnh")
        
    return addr.strip()

def normalize_nationality(raw_nat: str) -> str:
    """Normalizes nationality string to 'Việt Nam'."""
    if not raw_nat or raw_nat.strip() in ['"', "''", ""]:
        return "Việt Nam"
    clean = raw_nat.lower().strip()
    if "viet" in clean or "nam" in clean:
        return "Việt Nam"
    return raw_nat.strip()
