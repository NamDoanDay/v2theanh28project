"""
Search & Discovery Screen (Màn hình Tra cứu Hồ sơ).
Provides sub-millisecond query by citizen name (accented/unaccented), license number, birth year.
Includes 1-click jump to PDF page, open Excel, and open Windows Explorer.
"""
import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import List, Dict, Any, Optional, Callable

from src.database import DatabaseManager
from src.config import PROVINCE_CODES
from src.gui.pdf_viewer import PDFViewerFrame

class SearchScreenFrame(ctk.CTkFrame):
    def __init__(self, master, on_open_pdf_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_open_pdf_callback = on_open_pdf_callback
        self.db = DatabaseManager()
        self.current_results: List[Dict[str, Any]] = []

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        # 1. Top Search Header Banner
        self.top_frame = ctk.CTkFrame(self, fg_color=("#F0F4F8", "#1E2229"), corner_radius=6)
        self.top_frame.pack(fill="x", padx=10, pady=(10, 6))

        lbl_title = ctk.CTkLabel(
            self.top_frame,
            text="TRA CỨU HỒ SƠ GIẤY PHÉP LÁI XE LỊCH SỬ (CSDL ZERO-CONFIG)",
            font=("Segoe UI", 14, "bold"),
            text_color=("#1F497D", "#5B9BD5")
        )
        lbl_title.pack(anchor="w", padx=14, pady=(10, 4))

        # Search Controls Row
        self.search_row = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.search_row.pack(fill="x", padx=14, pady=(4, 10))

        # Province filter
        prov_options = ["Tất cả các tỉnh"] + [f"{p['code']} - {p['name']}" for p in PROVINCE_CODES]
        self.cmb_prov_filter = ctk.CTkComboBox(self.search_row, values=prov_options, width=170, height=34)
        self.cmb_prov_filter.set("Tất cả các tỉnh")
        self.cmb_prov_filter.pack(side="left", padx=(0, 8))

        # Query Entry
        self.txt_query = ctk.CTkEntry(
            self.search_row,
            placeholder_text="Nhập Số bằng (VD: A461544, C244138), Họ tên (có/không dấu: tran van yen), hoặc Năm sinh...",
            font=("Segoe UI", 12),
            height=34
        )
        self.txt_query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.txt_query.bind("<Return>", lambda e: self.perform_search())

        # Search Button
        self.btn_search = ctk.CTkButton(
            self.search_row,
            text="🔍 Tìm Kiếm",
            font=("Segoe UI", 12, "bold"),
            fg_color="#0066CC",
            hover_color="#004C99",
            width=110,
            height=34,
            command=self.perform_search
        )
        self.btn_search.pack(side="left", padx=(0, 8))

        # Sync from Excel Button
        self.btn_sync = ctk.CTkButton(
            self.search_row,
            text="🔄 Quét lại từ Excel",
            font=("Segoe UI", 11),
            fg_color=("gray75", "gray30"),
            width=135,
            height=34,
            command=self._sync_from_excel_folder
        )
        self.btn_sync.pack(side="left")

        # 2. Stats & Summary Bar
        self.stats_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_bar.pack(fill="x", padx=12, pady=(0, 4))

        self.lbl_stats = ctk.CTkLabel(
            self.stats_bar,
            text="Đang kết nối CSDL...",
            font=("Segoe UI", 11, "italic"),
            text_color=("gray40", "gray70")
        )
        self.lbl_stats.pack(side="left")

        self.lbl_result_count = ctk.CTkLabel(
            self.stats_bar,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color="#1E7E34"
        )
        self.lbl_result_count.pack(side="right")

        # 3. Search Results Scrollable Table
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray12"), corner_radius=6)
        self.results_scroll.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self._render_empty_placeholder("Nhập từ khóa và nhấn 'Tìm Kiếm' để tra cứu hồ sơ.")

    def refresh_stats(self):
        try:
            stats = self.db.get_stats()
            self.lbl_stats.configure(
                text=f"📊 Cơ sở dữ liệu: {stats['total_citizens']} công dân | {stats['total_dossiers']} cuốn sổ quản lý (gplx_index.db)"
            )
        except Exception:
            self.lbl_stats.configure(text="CSDL đã sẵn sàng.")

    def perform_search(self):
        q = self.txt_query.get().strip()
        if not q:
            self._render_empty_placeholder("Vui lòng nhập từ khóa tìm kiếm (Số bằng, Họ tên, hoặc Năm sinh).")
            return

        prov_sel = self.cmb_prov_filter.get().strip()
        prov_code = None
        if prov_sel and "-" in prov_sel:
            prov_code = prov_sel.split("-")[0].strip()

        try:
            results = self.db.search(query=q, province_code=prov_code, limit=150)
            self.current_results = results
            self._render_results(results)
        except Exception as e:
            messagebox.showerror("Lỗi Tra Cứu", f"Không thể tra cứu CSDL:\n{e}")

    def _render_empty_placeholder(self, text: str):
        for w in self.results_scroll.winfo_children():
            w.destroy()
        self.lbl_result_count.configure(text="")
        lbl = ctk.CTkLabel(self.results_scroll, text=text, font=("Segoe UI", 12, "italic"), text_color="gray50")
        lbl.pack(pady=40)

    def _render_results(self, results: List[Dict[str, Any]]):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        count = len(results)
        self.lbl_result_count.configure(text=f"Tìm thấy {count} kết quả phù hợp")

        if count == 0:
            self._render_empty_placeholder("Không tìm thấy người dân nào khớp với từ khóa tìm kiếm.")
            return

        # Table Header
        headers = [
            ("STT", 40),
            ("Họ và tên", 160),
            ("Năm sinh", 75),
            ("Số bằng", 100),
            ("Nơi cư trú", 170),
            ("HỘP", 50),
            ("HỘP SỐ", 65),
            ("Trang", 55),
            ("Thao tác", 280)
        ]

        header_frame = ctk.CTkFrame(self.results_scroll, fg_color=("#1F497D", "#1F497D"), corner_radius=3)
        header_frame.pack(fill="x", pady=(2, 4))

        for col_name, width in headers:
            lbl = ctk.CTkLabel(header_frame, text=col_name, width=width, font=("Segoe UI", 11, "bold"), text_color="white")
            lbl.pack(side="left", padx=3, pady=4)

        # Rows
        for idx, row in enumerate(results):
            row_bg = ("white", "#262626") if idx % 2 == 0 else ("#F8FAFC", "#1E1E1E")
            r_frame = ctk.CTkFrame(self.results_scroll, fg_color=row_bg, corner_radius=3)
            r_frame.pack(fill="x", pady=1)

            ctk.CTkLabel(r_frame, text=str(row.get("stt", idx + 1)), width=40, font=("Segoe UI", 11)).pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=row.get("full_name", ""), width=160, font=("Segoe UI", 11, "bold"), anchor="w").pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=str(row.get("birth_year", "")), width=75, font=("Segoe UI", 11)).pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=row.get("license_number", ""), width=100, font=("Segoe UI", 11, "bold"), text_color="#0066CC").pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=row.get("address", ""), width=170, font=("Segoe UI", 11), anchor="w").pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=str(row.get("box", "")), width=50, font=("Segoe UI", 11)).pack(side="left", padx=3)
            ctk.CTkLabel(r_frame, text=str(row.get("box_number", "")), width=65, font=("Segoe UI", 11)).pack(side="left", padx=3)

            p_num = row.get("page_number", 1)
            ctk.CTkLabel(r_frame, text=f"Trang {p_num}", width=55, font=("Segoe UI", 11)).pack(side="left", padx=3)

            # Action Buttons: [👁️ Xem PDF] [📊 Mở Excel] [📂 Thư mục]
            actions_frame = ctk.CTkFrame(r_frame, fg_color="transparent", width=280)
            actions_frame.pack(side="left", padx=3)

            pdf_p = row.get("pdf_path", "")
            xls_p = row.get("excel_path", "")

            btn_view_pdf = ctk.CTkButton(
                actions_frame,
                text=f"👁️ Xem PDF (P.{p_num})",
                font=("Segoe UI", 10, "bold"),
                width=105,
                height=24,
                fg_color="#0066CC",
                hover_color="#004C99",
                command=lambda p=pdf_p, pg=p_num: self._open_pdf_viewer(p, pg)
            )
            btn_view_pdf.pack(side="left", padx=2)

            btn_open_excel = ctk.CTkButton(
                actions_frame,
                text="📊 Excel",
                font=("Segoe UI", 10),
                width=65,
                height=24,
                fg_color="#1E7E34",
                hover_color="#155724",
                command=lambda xp=xls_p: self._open_external_file(xp)
            )
            btn_open_excel.pack(side="left", padx=2)

            btn_open_folder = ctk.CTkButton(
                actions_frame,
                text="📂 Thư mục",
                font=("Segoe UI", 10),
                width=75,
                height=24,
                fg_color=("gray70", "gray35"),
                hover_color=("gray60", "gray45"),
                command=lambda fp=pdf_p: self._open_containing_folder(fp)
            )
            btn_open_folder.pack(side="left", padx=2)

    def _open_pdf_viewer(self, pdf_path: str, page_num: int):
        if not os.path.exists(pdf_path):
            messagebox.showwarning("Không tìm thấy tệp", f"Tệp PDF không tồn tại tại đường dẫn:\n{pdf_path}")
            return

        if self.on_open_pdf_callback:
            self.on_open_pdf_callback(pdf_path, page_num)
        else:
            # Standalone pop-up viewer
            self._show_standalone_pdf_modal(pdf_path, page_num)

    def _show_standalone_pdf_modal(self, pdf_path: str, page_num: int):
        modal = ctk.CTkToplevel(self)
        modal.title(f"Hồ sơ PDF: {os.path.basename(pdf_path)} - Đang hiển thị trang {page_num}")
        modal.geometry("900x750")
        modal.after(100, modal.lift)

        viewer = PDFViewerFrame(modal)
        viewer.pack(fill="both", expand=True, padx=4, pady=4)
        viewer.load_pdf(pdf_path, initial_page=page_num)

    def _open_external_file(self, file_path: str):
        if not os.path.exists(file_path):
            messagebox.showwarning("Không tìm thấy tệp", f"Tệp Excel không tồn tại:\n{file_path}")
            return
        try:
            os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Lỗi mở tệp", f"Không thể mở tệp:\n{e}")

    def _open_containing_folder(self, file_path: str):
        if not os.path.exists(file_path):
            messagebox.showwarning("Không tìm thấy tệp", f"Đường dẫn không tồn tại:\n{file_path}")
            return
        try:
            subprocess.run(["explorer.exe", "/select,", os.path.abspath(file_path)])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục:\n{e}")

    def _sync_from_excel_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa các tệp Excel để đồng bộ vào CSDL")
        if not folder:
            return

        try:
            count = self.db.reindex_from_directory(folder)
            self.refresh_stats()
            messagebox.showinfo("Đồng bộ Thành công", f"Đã quét và đồng bộ thành công {count} cuốn sổ vào CSDL!")
        except Exception as e:
            messagebox.showerror("Lỗi đồng bộ", f"Có lỗi xảy ra khi quét thư mục:\n{e}")
