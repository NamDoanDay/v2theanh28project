"""
Entry point for the GPLX Desktop Application.
Usage:
    python app_desktop.py
"""
import sys
import os

# Ensure src is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import GPLXApp
from src.config import init_digitization_structure

def main():
    # Tự động khởi tạo cấu trúc thư mục chuẩn: So Hoa GPLX/DuLieuSoHoa_GPLS/[Tỉnh]/HOP/HoSo
    init_digitization_structure()
    
    app = GPLXApp()
    app.mainloop()

if __name__ == "__main__":
    main()
