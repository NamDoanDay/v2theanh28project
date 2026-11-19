"""
Portable Build Script for GPLX Management System using PyInstaller.
Creates a complete standalone, 1-click handover package:
📁 So Hoa GPLX/
├── 🚀 Chay_Ngay.bat
├── 📁 app/                           (GPLX_SoHoa_TraCuu.exe + bundled runtimes)
└── 📁 DuLieuSoHoa_GPLS/              (Pre-initialized provinces, boxes, dossiers)
    ├── 📁 LaoCai/HOP_01/HoSo_01/
    ├── 📁 TuyenQuang/HOP_01/HoSo_01/
    ├── 📁 DienBien/HOP_01/HoSo_01/
    └── ...
"""
import os
import sys
import shutil
import subprocess

def build():
    print("=" * 70)
    print(" BẮT ĐẦU ĐÓNG GÓI PORTABLE ỨNG DỤNG SỐ HÓA GPLX CHO NGƯỜI DÙNG NON-IT ")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    handover_dir = os.path.join(base_dir, "So Hoa GPLX")
    app_target_dir = os.path.join(handover_dir, "app")

    # Data files
    data_json = os.path.join(base_dir, "data", "province_codes.json")
    static_html = os.path.join(base_dir, "src", "server", "static", "index.html")

    datas = [
        f"{data_json};data/",
        f"{static_html};src/server/static/"
    ]

    datas_args = []
    for d in datas:
        datas_args.extend(["--add-data", d])

    collect_packages = [
        "customtkinter",
        "rapidocr_onnxruntime",
        "pypdfium2",
        "openpyxl",
        "fastapi",
        "uvicorn",
        "starlette"
    ]
    collect_args = []
    for pkg in collect_packages:
        collect_args.extend(["--collect-all", pkg])

    hidden_imports = [
        "PIL",
        "PIL.ImageTk",
        "qrcode",
        "sqlite3"
    ]
    hidden_args = []
    for h in hidden_imports:
        hidden_args.extend(["--hidden-import", h])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "GPLX_SoHoa_TraCuu",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
    ] + datas_args + collect_args + hidden_args + [
        os.path.join(base_dir, "app_desktop.py")
    ]

    print("[*] Đang thực thi lệnh PyInstaller (vui lòng đợi khoảng 1-2 phút)...")
    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode != 0:
        print("\n[!] Đóng gói thất bại với mã lỗi:", result.returncode)
        return False

    built_app_dir = os.path.join(dist_dir, "GPLX_SoHoa_TraCuu")
    if not os.path.exists(built_app_dir):
        print(f"[!] Không tìm thấy thư mục dist: {built_app_dir}")
        return False

    print("\n[*] Đang tổ chức thư mục bàn giao chuẩn 'So Hoa GPLX'...")
    os.makedirs(handover_dir, exist_ok=True)

    # 1. Di chuyển / sao chép ứng dụng đã build vào So Hoa GPLX/app
    if os.path.exists(app_target_dir):
        try:
            shutil.rmtree(app_target_dir)
        except Exception as e:
            print(f"[!] Cảnh báo không thể xóa app cũ: {e}")
    
    shutil.copytree(built_app_dir, app_target_dir)
    print(f"    -> Đã đưa ứng dụng vào: {app_target_dir}")

    # 2. Khởi tạo cấu trúc thư mục DuLieuSoHoa_GPLS và Chay_Ngay.bat
    sys.path.insert(0, base_dir)
    from src.config import init_digitization_structure
    dulieu_dir = init_digitization_structure(root_dir=handover_dir)
    print(f"    -> Đã khởi tạo kho dữ liệu: {dulieu_dir}")

    # 3. Sao chép sample PDF vào LaoCai/HOP_01/HoSo_01 để người dùng test ngay
    sample_src = os.path.join(base_dir, "samples", "sample_input.pdf")
    if os.path.exists(sample_src):
        sample_dst = os.path.join(dulieu_dir, "LaoCai", "HOP_01", "HoSo_01", "sample_input.pdf")
        shutil.copyfile(sample_src, sample_dst)
        print(f"    -> Đã sao chép file scan mẫu: {sample_dst}")

    print("\n" + "=" * 70)
    print(">>> ĐÓNG GÓI HOÀN TẤT VÀ SẴN SÀNG BÀN GIAO CHO NGƯỜI DÙNG NON-IT! <<<")
    print(f"Vị trí gói bàn giao: {handover_dir}")
    print("Cấu trúc:")
    print("  So Hoa GPLX/")
    print("  ├── Chay_Ngay.bat                (Nhấp đúp chuột để mở app)")
    print("  ├── app/                        (Ứng dụng độc lập + thư viện)")
    print("  │   └── GPLX_SoHoa_TraCuu.exe")
    print("  └── DuLieuSoHoa_GPLS/           (Kho dữ liệu chuẩn hóa Tỉnh/Hộp/Hồ sơ)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    build()
