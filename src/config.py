"""
Configuration and constants for GPLX Digitization and Renaming System.
"""
import os
import sys
import json
import re

# Determine BASE_DIR (works for both dev source and PyInstaller frozen app)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller bundle.
    """
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            cand = os.path.join(meipass, relative_path)
            if os.path.exists(cand):
                return cand
        exe_dir = os.path.dirname(sys.executable)
        cand_exe = os.path.join(exe_dir, relative_path)
        if os.path.exists(cand_exe):
            return cand_exe
    return os.path.join(BASE_DIR, relative_path)

DATA_DIR = os.path.join(BASE_DIR, "data")
PROVINCE_CODES_FILE = get_resource_path(os.path.join("data", "province_codes.json"))

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
        try:
            with open(PROVINCE_CODES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to local data folder if available
    local_path = os.path.join(BASE_DIR, "data", "province_codes.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

PROVINCE_CODES = load_province_codes()

def find_province_code_by_text(text: str) -> str:
    """
    Search for matching province name or keywords from extracted text.
    Returns 2-digit code (e.g. '15') or fallback '15'.
    """
    if not text:
        return "15" # Default fallback
    
    text_lower = text.lower()
    for prov in PROVINCE_CODES:
        for kw in prov.get("keywords", []):
            if kw in text_lower:
                return prov["code"]
    return "15"

def get_handover_root_dir() -> str:
    """
    Xác định thư mục gốc 'So Hoa GPLX'.
    - Nếu app nằm trong '.../So Hoa GPLX/app': trả về '.../So Hoa GPLX'
    - Nếu chạy từ mã nguồn repo: trả về '[repo]/So Hoa GPLX'
    """
    parent = os.path.dirname(BASE_DIR)
    if os.path.basename(BASE_DIR).lower() == "app" or os.path.basename(parent).lower() == "so hoa gplx":
        return parent
    return os.path.join(BASE_DIR, "So Hoa GPLX")

def get_default_dulieu_dir() -> str:
    """
    Trả về đường dẫn tới thư mục DuLieuSoHoa_GPLS.
    """
    root = get_handover_root_dir()
    dulieu_dir = os.path.join(root, "DuLieuSoHoa_GPLS")
    if not os.path.exists(dulieu_dir):
        dulieu_dir = os.path.join(BASE_DIR, "DuLieu_GPLX")
    return dulieu_dir

def init_digitization_structure(root_dir: str = None) -> str:
    """
    Tự động khởi tạo cấu trúc thư mục chuẩn bàn giao cho người dùng Non-IT:
    📁 So Hoa GPLX/
    ├── 🚀 Chay_Ngay.bat
    ├── 📁 app/
    └── 📁 DuLieuSoHoa_GPLS/
        ├── LaoCai/HOP_01/HoSo_01/
        ├── TuyenQuang/HOP_01/HoSo_01/
        ├── DienBien/HOP_01/HoSo_01/
        ├── SonLa/HOP_01/HoSo_01/
        ├── HaGiang/HOP_01/HoSo_01/
        ├── YenBai/HOP_01/HoSo_01/
        ├── CaoBang/HOP_01/HoSo_01/
        ├── LangSon/HOP_01/HoSo_01/
        ├── PhuTho/HOP_01/HoSo_01/
        ├── BacKan/HOP_01/HoSo_01/
        ├── HoaBinh/HOP_01/HoSo_01/
        └── LaiChau/HOP_01/HoSo_01/
    Trả về đường dẫn tới thư mục DuLieuSoHoa_GPLS.
    """
    if not root_dir:
        root_dir = get_handover_root_dir()

    os.makedirs(root_dir, exist_ok=True)

    # 1. Tạo file Chay_Ngay.bat ở thư mục gốc So Hoa GPLX
    bat_path = os.path.join(root_dir, "Chay_Ngay.bat")
    if not os.path.exists(bat_path):
        bat_content = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "title HỆ THỐNG SỐ HÓA & TRA CỨU GIẤY PHÉP LÁI XE\r\n"
            "echo ========================================================\r\n"
            "echo   HỆ THỐNG SỐ HÓA VÀ TRA CỨU GIẤY PHÉP LÁI XE (GPLX)\r\n"
            "echo ========================================================\r\n"
            "echo.\r\n"
            "echo [*] Đang khởi động ứng dụng, vui lòng chờ trong giây lát...\r\n"
            "cd /d \"%~dp0app\"\r\n"
            "if exist \"GPLX_SoHoa_TraCuu.exe\" (\r\n"
            "    start \"\" \"GPLX_SoHoa_TraCuu.exe\"\r\n"
            ") else (\r\n"
            "    if exist \"..\\app_desktop.py\" (\r\n"
            "        python \"..\\app_desktop.py\"\r\n"
            "    ) else (\r\n"
            "        echo [!] Không tìm thấy GPLX_SoHoa_TraCuu.exe trong thư mục app.\r\n"
            "        pause\r\n"
            "    )\r\n"
            ")\r\n"
            "exit\r\n"
        )
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
        except Exception:
            pass

    # 2. Tạo thư mục app
    app_dir = os.path.join(root_dir, "app")
    os.makedirs(app_dir, exist_ok=True)

    # 3. Tạo kho dữ liệu số hóa theo tỉnh/hộp/hồ sơ
    dulieu_dir = os.path.join(root_dir, "DuLieuSoHoa_GPLS")
    os.makedirs(dulieu_dir, exist_ok=True)

    provinces = [
        "LaoCai", "TuyenQuang", "DienBien", "SonLa",
        "HaGiang", "YenBai", "CaoBang", "LangSon",
        "PhuTho", "BacKan", "HoaBinh", "LaiChau"
    ]
    for prov in provinces:
        hoso_dir = os.path.join(dulieu_dir, prov, "HOP_01", "HoSo_01")
        os.makedirs(hoso_dir, exist_ok=True)

    # 4. Tạo file hướng dẫn lưu trữ tại DuLieuSoHoa_GPLS
    readme_path = os.path.join(dulieu_dir, "HUONG_DAN_LUU_TRU.txt")
    if not os.path.exists(readme_path):
        readme_content = (
            "====================================================================\r\n"
            "QUY TẮC LƯU TRỮ VÀ TỔ CHỨC FILE SCAN PDF SỐ HÓA GPLX\r\n"
            "====================================================================\r\n\r\n"
            "1. CẤU TRÚC THƯ MỤC:\r\n"
            "   DuLieuSoHoa_GPLS/\r\n"
            "   ├── [Tên_Tỉnh]/              (Ví dụ: LaoCai, TuyenQuang, DienBien,...)\r\n"
            "   │   └── HOP_[Số_Hộp]/        (Ví dụ: HOP_01, HOP_02, ...)\r\n"
            "   │       └── HoSo_[Số_Hồ_Sơ]/ (Ví dụ: HoSo_01, HoSo_02, ...)\r\n"
            "   │           └── [Các file scan PDF]\r\n\r\n"
            "2. HƯỚNG DẪN THỰC HIỆN ĐỔI TÊN HÀNG LOẠT:\r\n"
            "   - Đặt các file PDF scan gốc vào thư mục HoSo tương ứng.\r\n"
            "   - Mở ứng dụng, chọn tab 'Số hóa & Đổi tên hồ sơ'.\r\n"
            "   - Nhấn nút '📁 Đổi tên file (theo folder)'.\r\n"
            "   - Chọn thư mục HoSo vừa đặt file PDF.\r\n"
            "   - Hệ thống sẽ tự động quét, đọc bìa và bảng, sau đó tạo file PDF mới\r\n"
            "     được đổi tên chuẩn xác theo quy định: [Mã tỉnh].[SQL].[Tháng].[Năm].[Số đầu]-[Số cuối].pdf\r\n"
            "     (Đồng thời giữ nguyên 100% file gốc ban đầu để đối chiếu an toàn tuyệt đối).\r\n"
        )
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
        except Exception:
            pass

    return dulieu_dir
