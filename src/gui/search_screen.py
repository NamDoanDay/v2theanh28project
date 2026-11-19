"""
Search & Discovery Screen (Màn hình Tra cứu Hồ sơ & Mở file scan).
Provides:
- Mode 1: 👤 Tra Cứu Công Dân: Sub-millisecond query by citizen name, license number, birth year.
- Mode 2: 📁 Danh Mục Sổ / File Excel Đã Import: Complete inventory of imported Excel files,
          boxes (Hộp), folders (Hộp số), and provinces with 1-click citizen drill-down.
Includes 1-click jump to PDF page, open companion Excel, and open Windows Explorer.
"""
import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import List, Dict, Any, Optional, Callable

from src.database import DatabaseManager
from src.config import PROVINCE_CODES, get_default_dulieu_dir
from src.gui.pdf_viewer import PDFViewerFrame

class SearchScreenFrame(ctk.CTkFrame):
    def __init__(self, master, on_open_pdf_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_open_pdf_callback = on_open_pdf_callback
        self.db = DatabaseManager()
        self.current_citizen_results: List[Dict[str, Any]] = []
        self.current_dossier_results: List[Dict[str, Any]] = []
        self.current_mode = "👤 Tra Cứu Công Dân"

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        # 1. Top Header Banner
        self.top_frame = ctk.CTkFrame(self, fg_color=("#F0F4F8", "#1E2229"), corner_radius=6)
        self.top_frame.pack(fill="x", padx=10, pady=(10, 6))

        top_header_row = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        top_header_row.pack(fill="x", padx=14, pady=(8, 4))

        lbl_title = ctk.CTkLabel(
            top_header_row,
            text="HỆ THỐNG TRA CỨU & QUẢN LÝ HỒ SƠ GIẤY PHÉP LÁI XE LỊCH SỬ",
            font=("Segoe UI", 13, "bold"),
            text_color=("#1F497D", "#5B9BD5")
        )
        lbl_title.pack(side="left")

        # Mode Selector (Toggle between Citizen search & Dossier Inventory)
        self.mode_toggle = ctk.CTkSegmentedButton(
            top_header_row,
            values=["👤 Tra Cứu Công Dân", "📁 Danh Mục Sổ / File Excel Đã Import"],
            font=("Segoe UI", 11, "bold"),
            selected_color="#0066CC",
            height=28,
            command=self.on_mode_change
        )
        self.mode_toggle.set(self.current_mode)
        self.mode_toggle.pack(side="right")

        # --- SUB-PANEL 1: Citizen Search Controls ---
        self.citizen_search_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.citizen_search_frame.pack(fill="x", padx=14, pady=(4, 8))

        prov_options = ["Tất cả các tỉnh"] + [f"{p['code']} - {p['name']}" for p in PROVINCE_CODES]
        self.cmb_prov_filter = ctk.CTkComboBox(self.citizen_search_frame, values=prov_options, width=170, height=34)
        self.cmb_prov_filter.set("Tất cả các tỉnh")
        self.cmb_prov_filter.pack(side="left", padx=(0, 8))

        self.txt_query = ctk.CTkEntry(
            self.citizen_search_frame,
            placeholder_text="Nhập Số bằng (VD: A461544, C244138), Họ tên (có/không dấu: tran van yen), hoặc Năm sinh...",
            font=("Segoe UI", 12),
            height=34
        )
        self.txt_query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.txt_query.bind("<Return>", lambda e: self.perform_citizen_search())

        self.btn_search = ctk.CTkButton(
            self.citizen_search_frame,
            text="🔍 Tìm Kiếm",
            font=("Segoe UI", 12, "bold"),
            fg_color="#0066CC",
            hover_color="#004C99",
            width=110,
            height=34,
            command=self.perform_citizen_search
        )
        self.btn_search.pack(side="left", padx=(0, 8))

        self.btn_sync = ctk.CTkButton(
            self.citizen_search_frame,
            text="🔄 Quét lại từ Excel",
            font=("Segoe UI", 11),
            fg_color=("gray75", "gray30"),
            width=135,
            height=34,
            command=self._sync_from_excel_folder
        )
        self.btn_sync.pack(side="left")

        # --- SUB-PANEL 2: Dossier Inventory Controls (Initially Hidden) ---
        self.dossier_search_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")

        self.cmb_dossier_prov = ctk.CTkComboBox(self.dossier_search_frame, values=prov_options, width=170, height=34, command=lambda e: self._on_dossier_prov_changed())
        self.cmb_dossier_prov.set("Tất cả các tỉnh")
        self.cmb_dossier_prov.pack(side="left", padx=(0, 8))

        self.cmb_dossier_box = ctk.CTkComboBox(self.dossier_search_frame, values=["Tất cả các Hộp"], width=130, height=34)
        self.cmb_dossier_box.set("Tất cả các Hộp")
        self.cmb_dossier_box.pack(side="left", padx=(0, 8))

        self.txt_dossier_kw = ctk.CTkEntry(
            self.dossier_search_frame,
            placeholder_text="Lọc theo Tên file Excel/PDF, Số Hộp, hoặc Hộp số...",
            font=("Segoe UI", 12),
            height=34
        )
        self.txt_dossier_kw.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.txt_dossier_kw.bind("<Return>", lambda e: self.perform_dossier_search())

        self.btn_filter_dossier = ctk.CTkButton(
            self.dossier_search_frame,
            text="🔍 Lọc Danh Sách",
            font=("Segoe UI", 12, "bold"),
            fg_color="#0D9488",
            hover_color="#0F766E",
            width=120,
            height=34,
            command=self.perform_dossier_search
        )
        self.btn_filter_dossier.pack(side="left", padx=(0, 8))

        self.btn_refresh_dossier = ctk.CTkButton(
            self.dossier_search_frame,
            text="🔄 Làm mới",
            font=("Segoe UI", 11),
            fg_color=("gray75", "gray30"),
            width=90,
            height=34,
            command=self.perform_dossier_search
        )
        self.btn_refresh_dossier.pack(side="left")

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

        # 3. Scrollable Table
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray12"), corner_radius=6)
        self.results_scroll.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self._render_empty_placeholder("Nhập từ khóa và nhấn 'Tìm Kiếm' để tra cứu hồ sơ người lái xe.")

    def on_mode_change(self, mode: str):
        self.current_mode = mode
        if mode == "👤 Tra Cứu Công Dân":
            self.dossier_search_frame.pack_forget()
            self.citizen_search_frame.pack(fill="x", padx=14, pady=(4, 8))
            self.refresh_stats()
            if self.current_citizen_results:
                self._render_citizen_results(self.current_citizen_results)
            else:
                self._render_empty_placeholder("Nhập từ khóa và nhấn 'Tìm Kiếm' để tra cứu hồ sơ người lái xe.")
        else:
            self.citizen_search_frame.pack_forget()
            self.dossier_search_frame.pack(fill="x", padx=14, pady=(4, 8))
            self._update_box_filter_options()
            self.perform_dossier_search()

    def refresh_stats(self):
        try:
            inv = self.db.get_inventory_stats()
            if self.current_mode == "📁 Danh Mục Sổ / File Excel Đã Import":
                self.lbl_stats.configure(
                    text=f"📊 Đã import: {inv['total_provinces']} tỉnh | {inv['total_boxes']} Tủ/Hộp | {inv['total_box_numbers']} Hộp số | {inv['total_dossiers']} cuốn sổ/file Excel ({inv['total_citizens']} GPLX)"
                )
            else:
                self.lbl_stats.configure(
                    text=f"📊 Cơ sở dữ liệu: {inv['total_citizens']} công dân | {inv['total_dossiers']} cuốn sổ quản lý (gplx_index.db)"
                )
        except Exception:
            self.lbl_stats.configure(text="CSDL đã sẵn sàng.")

    def _on_dossier_prov_changed(self):
        self._update_box_filter_options()
        self.perform_dossier_search()

    def _update_box_filter_options(self):
        prov_sel = self.cmb_dossier_prov.get().strip()
        prov_code = "all"
        if prov_sel and "-" in prov_sel:
            prov_code = prov_sel.split("-")[0].strip()

        boxes = self.db.get_distinct_boxes(province_code=prov_code)
        options = ["Tất cả các Hộp"] + [f"Hộp {b}" for b in boxes]
        self.cmb_dossier_box.configure(values=options)
        self.cmb_dossier_box.set("Tất cả các Hộp")

    # ==========================================
    # MODE 1: CITIZEN SEARCH
    # ==========================================

    def perform_citizen_search(self, dossier_id: Optional[int] = None):
        q = self.txt_query.get().strip()
        if not q and not dossier_id:
            self._render_empty_placeholder("Vui lòng nhập từ khóa tìm kiếm (Số bằng, Họ tên, hoặc Năm sinh).")
            return

        prov_sel = self.cmb_prov_filter.get().strip()
        prov_code = None
        if prov_sel and "-" in prov_sel:
            prov_code = prov_sel.split("-")[0].strip()

        try:
            results = self.db.search(query=q, province_code=prov_code, dossier_id=dossier_id, limit=200)
            self.current_citizen_results = results
            self._render_citizen_results(results)
        except Exception as e:
            messagebox.showerror("Lỗi Tra Cứu", f"Không thể tra cứu CSDL:\n{e}")

    def _render_citizen_results(self, results: List[Dict[str, Any]]):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        count = len(results)
        self.lbl_result_count.configure(text=f"Tìm thấy {count} kết quả công dân")

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

    # ==========================================
    # MODE 2: DOSSIER & EXCEL INVENTORY
    # ==========================================

    def perform_dossier_search(self):
        prov_sel = self.cmb_dossier_prov.get().strip()
        prov_code = "all"
        if prov_sel and "-" in prov_sel:
            prov_code = prov_sel.split("-")[0].strip()

        box_sel = self.cmb_dossier_box.get().strip()
        box_val = "all"
        if box_sel and box_sel != "Tất cả các Hộp":
            box_val = box_sel.replace("Hộp", "").strip()

        kw = self.txt_dossier_kw.get().strip()

        try:
            dossiers = self.db.get_all_dossiers(province_code=prov_code, box=box_val, search_kw=kw, limit=200)
            self.current_dossier_results = dossiers
            self._render_dossier_results(dossiers)
            self.refresh_stats()
        except Exception as e:
            messagebox.showerror("Lỗi Truy Vấn", f"Không thể lấy danh sách cuốn sổ đã nạp:\n{e}")

    def _render_dossier_results(self, dossiers: List[Dict[str, Any]]):
        for w in self.results_scroll.winfo_children():
            w.destroy()

        count = len(dossiers)
        self.lbl_result_count.configure(text=f"Có {count} cuốn sổ / file Excel trong CSDL")

        if count == 0:
            self._render_empty_placeholder("Chưa có cuốn sổ hoặc file Excel nào được import vào hệ thống phù hợp với bộ lọc.")
            return

        # Dossier Table Headers
        headers = [
            ("STT", 35),
            ("Tỉnh", 55),
            ("HỘP", 50),
            ("H.SỐ", 60),
            ("Tên File PDF / Excel", 240),
            ("Hạng", 50),
            ("Ngày bìa", 85),
            ("Số GPLX", 65),
            ("Dãy số GPLX", 170),
            ("Đánh giá", 95),
            ("Thao tác", 270)
        ]

        header_frame = ctk.CTkFrame(self.results_scroll, fg_color=("#0F766E", "#0F766E"), corner_radius=3)
        header_frame.pack(fill="x", pady=(2, 4))

        for col_name, width in headers:
            lbl = ctk.CTkLabel(header_frame, text=col_name, width=width, font=("Segoe UI", 11, "bold"), text_color="white")
            lbl.pack(side="left", padx=2, pady=4)

        # Rows
        for idx, d in enumerate(dossiers, start=1):
            row_bg = ("white", "#262626") if idx % 2 == 1 else ("#F0FDFA", "#1A2E2B")
            r_frame = ctk.CTkFrame(self.results_scroll, fg_color=row_bg, corner_radius=3)
            r_frame.pack(fill="x", pady=1)

            ctk.CTkLabel(r_frame, text=str(idx), width=35, font=("Segoe UI", 11)).pack(side="left", padx=2)
            ctk.CTkLabel(r_frame, text=str(d.get("province_code", "")), width=55, font=("Segoe UI", 11, "bold"), text_color="#0D9488").pack(side="left", padx=2)
            ctk.CTkLabel(r_frame, text=str(d.get("box", "-")), width=50, font=("Segoe UI", 11)).pack(side="left", padx=2)
            ctk.CTkLabel(r_frame, text=str(d.get("box_number", "-")), width=60, font=("Segoe UI", 11)).pack(side="left", padx=2)

            fname = d.get("final_filename", "")
            ctk.CTkLabel(r_frame, text=fname, width=240, font=("Consolas", 10.5, "bold"), anchor="w").pack(side="left", padx=2)

            lic_cls = d.get("license_class") or "A1"
            ctk.CTkLabel(r_frame, text=lic_cls, width=50, font=("Segoe UI", 11)).pack(side="left", padx=2)

            ex_date = d.get("exam_date") or "-"
            ctk.CTkLabel(r_frame, text=ex_date, width=85, font=("Segoe UI", 11)).pack(side="left", padx=2)

            total_c = d.get("total_citizens", 0)
            ctk.CTkLabel(r_frame, text=f"{total_c} bằng", width=65, font=("Segoe UI", 11, "bold"), text_color="#2563EB").pack(side="left", padx=2)

            seq = d.get("license_sequence") or "-"
            ctk.CTkLabel(r_frame, text=seq, width=170, font=("Segoe UI", 10), anchor="w").pack(side="left", padx=2)

            note = d.get("status_note") or "Đủ"
            note_color = "#16A34A" if "Đủ" in note else "#EA580C"
            ctk.CTkLabel(r_frame, text=note, width=95, font=("Segoe UI", 10.5, "bold"), text_color=note_color).pack(side="left", padx=2)

            # Actions: [👥 Xem Dân] [👁️ PDF] [📊 Excel]
            actions_frame = ctk.CTkFrame(r_frame, fg_color="transparent", width=270)
            actions_frame.pack(side="left", padx=2)

            d_id = d.get("id")
            pdf_p = d.get("pdf_path", "")
            xls_p = d.get("excel_path", "")

            btn_drill_down = ctk.CTkButton(
                actions_frame,
                text="👥 Xem Dân",
                font=("Segoe UI", 10, "bold"),
                width=80,
                height=24,
                fg_color="#2563EB",
                hover_color="#1D4ED8",
                command=lambda did=d_id, fn=fname: self.drill_down_to_dossier_citizens(did, fn)
            )
            btn_drill_down.pack(side="left", padx=2)

            btn_pdf = ctk.CTkButton(
                actions_frame,
                text="👁️ PDF",
                font=("Segoe UI", 10),
                width=60,
                height=24,
                fg_color="#0066CC",
                hover_color="#004C99",
                command=lambda p=pdf_p: self._open_pdf_viewer(p, 1)
            )
            btn_pdf.pack(side="left", padx=2)

            btn_excel = ctk.CTkButton(
                actions_frame,
                text="📊 Excel",
                font=("Segoe UI", 10),
                width=60,
                height=24,
                fg_color="#16A34A",
                hover_color="#15803D",
                command=lambda xp=xls_p: self._open_external_file(xp)
            )
            btn_excel.pack(side="left", padx=2)

            btn_folder = ctk.CTkButton(
                actions_frame,
                text="📂",
                font=("Segoe UI", 10),
                width=32,
                height=24,
                fg_color=("gray70", "gray35"),
                hover_color=("gray60", "gray45"),
                command=lambda fp=pdf_p: self._open_containing_folder(fp)
            )
            btn_folder.pack(side="left", padx=2)

    def drill_down_to_dossier_citizens(self, dossier_id: int, dossier_name: str):
        """Switches view to Citizen Mode and displays all citizens belonging to this dossier."""
        self.mode_toggle.set("👤 Tra Cứu Công Dân")
        self.on_mode_change("👤 Tra Cứu Công Dân")
        self.txt_query.delete(0, "end")
        self.txt_query.insert(0, f"")
        self.lbl_stats.configure(text=f"📂 Đang hiển thị danh sách công dân trong cuốn sổ: {dossier_name}")
        self.perform_citizen_search(dossier_id=dossier_id)

    # ==========================================
    # COMMON UTILITIES
    # ==========================================

    def _render_empty_placeholder(self, text: str):
        for w in self.results_scroll.winfo_children():
            w.destroy()
        self.lbl_result_count.configure(text="")
        lbl = ctk.CTkLabel(self.results_scroll, text=text, font=("Segoe UI", 12, "italic"), text_color="gray50")
        lbl.pack(pady=40)

    def _open_pdf_viewer(self, pdf_path: str, page_num: int):
        if not os.path.exists(pdf_path):
            messagebox.showwarning("Không tìm thấy tệp", f"Tệp PDF không tồn tại tại đường dẫn:\n{pdf_path}")
            return

        if self.on_open_pdf_callback:
            self.on_open_pdf_callback(pdf_path, page_num)
        else:
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
        folder = filedialog.askdirectory(
            title="Chọn thư mục chứa các tệp Excel để đồng bộ vào CSDL",
            initialdir=get_default_dulieu_dir()
        )
        if not folder:
            return

        try:
            count = self.db.reindex_from_directory(folder)
            self.refresh_stats()
            messagebox.showinfo("Đồng bộ Thành công", f"Đã quét và đồng bộ thành công {count} cuốn sổ vào CSDL!")
        except Exception as e:
            messagebox.showerror("Lỗi đồng bộ", f"Có lỗi xảy ra khi quét thư mục:\n{e}")
