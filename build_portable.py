"""
Portable Build Script for GPLX Management System using PyInstaller.
Creates a standalone Windows executable or directory for deployment on portable SSD.
"""
import os
import sys
import subprocess
import customtkinter

def build():
    print("=" * 65)
    print("BẮT ĐẦU ĐÓNG GÓI PORTABLE ỨNG DỤNG SỐ HÓA GPLX (PYINSTALLER)")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ctk_dir = os.path.dirname(customtkinter.__file__)

    # Collect data files
    data_json = os.path.join(base_dir, "data", "province_codes.json")
    static_html = os.path.join(base_dir, "src", "server", "static", "index.html")

    datas = [
        f"{ctk_dir};customtkinter/",
        f"{data_json};data/",
        f"{static_html};src/server/static/"
    ]

    datas_args = []
    for d in datas:
        datas_args.extend(["--add-data", d])

    hidden_imports = [
        "customtkinter",
        "rapidocr_onnxruntime",
        "onnxruntime",
        "pypdfium2",
        "openpyxl",
        "PIL",
        "PIL.ImageTk",
        "fastapi",
        "uvicorn",
        "qrcode",
        "sqlite3",
        "starlette"
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
    ] + datas_args + hidden_args + [
        os.path.join(base_dir, "app_desktop.py")
    ]

    print("[*] Đang thực thi lệnh đóng gói:")
    print(" ".join(cmd[:8]) + " ...")

    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode == 0:
        dist_dir = os.path.join(base_dir, "dist", "GPLX_SoHoa_TraCuu")
        print("\n" + "=" * 65)
        print(">>> ĐÓNG GÓI PORTABLE THÀNH CÔNG! <<<")
        print(f"Thư mục ứng dụng đã tạo tại:\n{dist_dir}")
        print("=" * 65)
        return True
    else:
        print("\n[!] Đóng gói thất bại với mã lỗi:", result.returncode)
        return False

if __name__ == "__main__":
    build()
