@echo off
setlocal
chcp 65001 >nul
title Build So Hoa GPLX
cd /d "%~dp0"

echo ================================================
echo        BUILD UNG DUNG SO HOA GPLX
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 goto missing_python

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 goto missing_pyinstaller

echo Dang build va cap nhat goi "So Hoa GPLX"...
python "%~dp0build_portable.py"
if errorlevel 1 goto build_failed

if not exist "%~dp0So Hoa GPLX\app\GPLX_SoHoa_TraCuu.exe" goto missing_output

echo.
echo BUILD THANH CONG.
echo Goi ung dung: "%~dp0So Hoa GPLX"
echo Mo file "Chay_Ngay.bat" trong goi de chay ung dung.
goto finish

:missing_python
echo Khong tim thay Python tren PATH. Hay cai Python va thu lai.
goto failed

:missing_pyinstaller
echo Khong tim thay PyInstaller. Cai dat bang lenh:
echo     python -m pip install pyinstaller
goto failed

:build_failed
echo Build that bai. Xem loi ben tren de biet chi tiet.
goto failed

:missing_output
echo Build ket thuc nhung khong tim thay file EXE trong goi ban giao.
goto failed

:failed
echo.
pause
exit /b 1

:finish
echo.
pause
exit /b 0
