"""
Review & Quick Edit Panel (Right Column).
Displays extracted metadata, proposed filename, sequence analysis, and editable citizen grid.
"""
import customtkinter as ctk
from typing import Dict, Any, List, Callable, Optional

class ReviewPanel(ctk.CTkFrame):
    def __init__(self, master, on_confirm_callback: Callable, on_page_jump_callback: Callable, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_confirm_callback = on_confirm_callback
        self.on_page_jump_callback = on_page_jump_callback
        self.current_data: Optional[Dict[str, Any]] = None
        self.citizen_entries: List[Dict[str, Any]] = []

        self._build_ui()

    def _build_ui(self):
        # 1. Top Section: Proposed Filename Banner
        self.banner_frame = ctk.CTkFrame(self, fg_color=("#EBF3FB", "#1F2D3D"), corner_radius=6)
        self.banner_frame.pack(fill="x", padx=6, pady=(6, 4))

        lbl_fn_title = ctk.CTkLabel(self.banner_frame, text="TÊN FILE ĐỀ XUẤT (QUY TẮC LƯU TRỮ):", font=("Segoe UI", 11, "bold"), text_color=("#1F497D", "#5B9BD5"))
        lbl_fn_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.txt_proposed_filename = ctk.CTkEntry(self.banner_frame, font=("Consolas", 13, "bold"), height=32)
        self.txt_proposed_filename.pack(fill="x", padx=10, pady=(0, 8))

        # 2. Middle Section: Metadata Cards in Scrollable Container
        self.scroll_form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_form.pack(fill="both", expand=True, padx=6, pady=2)

        # Card A: Metadata bìa & Hộp số
        lbl_card_a = ctk.CTkLabel(self.scroll_form, text="THÔNG TIN BÌA SỔ & VỊ TRÍ HỒ SƠ", font=("Segoe UI", 12, "bold"))
        lbl_card_a.pack(anchor="w", pady=(4, 2))

        self.card_a = ctk.CTkFrame(self.scroll_form, corner_radius=6)
        self.card_a.pack(fill="x", pady=2)

        # Grid row 1: Loại sổ, Ngày bìa
        ctk.CTkLabel(self.card_a, text="Loại sổ:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.txt_book_type = ctk.CTkEntry(self.card_a, height=28)
        self.txt_book_type.grid(row=0, column=1, columnspan=3, sticky="ew", padx=8, pady=4)

        # Grid row 2: Ngày bìa, Hạng, Khóa
        ctk.CTkLabel(self.card_a, text="Ngày bìa sổ:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.txt_cover_date = ctk.CTkEntry(self.card_a, width=120, height=28)
        self.txt_cover_date.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(self.card_a, text="Hạng / Khóa:").grid(row=1, column=2, sticky="w", padx=8, pady=4)
        self.frame_hang_khoa = ctk.CTkFrame(self.card_a, fg_color="transparent")
        self.frame_hang_khoa.grid(row=1, column=3, sticky="w", padx=8, pady=4)
        self.txt_hang = ctk.CTkEntry(self.frame_hang_khoa, width=50, height=28)
        self.txt_hang.pack(side="left", padx=(0, 4))
        self.txt_khoa = ctk.CTkEntry(self.frame_hang_khoa, width=60, height=28)
        self.txt_khoa.pack(side="left")

        # Grid row 3: HỘP, HỘP SỐ
        ctk.CTkLabel(self.card_a, text="HỘP (Tủ HS):").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.txt_box = ctk.CTkEntry(self.card_a, width=120, height=28)
        self.txt_box.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(self.card_a, text="HỘP SỐ (Hộp giấy):").grid(row=2, column=2, sticky="w", padx=8, pady=4)
        self.txt_box_number = ctk.CTkEntry(self.card_a, width=120, height=28)
        self.txt_box_number.grid(row=2, column=3, sticky="w", padx=8, pady=4)

        self.card_a.grid_columnconfigure(1, weight=1)
        self.card_a.grid_columnconfigure(3, weight=1)

        # Card B: Rà soát dãy số & Nhận định
        lbl_card_b = ctk.CTkLabel(self.scroll_form, text="RÀ SOÁT DÃY SỐ GPLX & NHẬN ĐỊNH", font=("Segoe UI", 12, "bold"))
        lbl_card_b.pack(anchor="w", pady=(10, 2))

        self.card_b = ctk.CTkFrame(self.scroll_form, corner_radius=6)
        self.card_b.pack(fill="x", pady=2)

        ctk.CTkLabel(self.card_b, text="Tổng số GPLX:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.txt_total_gplx = ctk.CTkEntry(self.card_b, width=80, height=28)
        self.txt_total_gplx.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(self.card_b, text="Nhận định:").grid(row=0, column=2, sticky="w", padx=8, pady=4)
        self.opt_status_note = ctk.CTkOptionMenu(
            self.card_b,
            values=["Đủ", "Ngắt, không theo thứ tự"],
            width=170,
            height=28
        )
        self.opt_status_note.grid(row=0, column=3, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(self.card_b, text="Dãy số GPLX:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.txt_seq_summary = ctk.CTkEntry(self.card_b, height=28)
        self.txt_seq_summary.grid(row=1, column=1, columnspan=3, sticky="ew", padx=8, pady=4)

        self.card_b.grid_columnconfigure(1, weight=1)
        self.card_b.grid_columnconfigure(3, weight=1)

        # Card C: Editable Citizens Grid
        lbl_card_c = ctk.CTkLabel(self.scroll_form, text="DANH SÁCH CÔNG DÂN TRONG SỔ (CLICK DÒNG ĐỂ NHẢY TRANG PDF)", font=("Segoe UI", 12, "bold"))
        lbl_card_c.pack(anchor="w", pady=(10, 2))

        self.grid_frame = ctk.CTkFrame(self.scroll_form, corner_radius=6)
        self.grid_frame.pack(fill="both", expand=True, pady=2)

        # 3. Bottom Action Bar
        self.bottom_bar = ctk.CTkFrame(self, height=55, fg_color=("gray85", "gray20"))
        self.bottom_bar.pack(fill="x", padx=6, pady=(4, 6))

        # Initially disabled until OCR data is loaded
        self.btn_confirm = ctk.CTkButton(
            self.bottom_bar,
            text="✔ XÁC NHẬN: ĐỔI TÊN PDF & XUẤT EXCEL & CẬP NHẬT TỔNG HỢP",
            font=("Segoe UI", 13, "bold"),
            fg_color="gray50",
            hover_color="#155724",
            state="disabled",
            height=38,
            command=self._handle_confirm
        )
        self.btn_confirm.pack(fill="x", padx=10, pady=8)

    def load_data(self, dossier_data: Dict[str, Any]):
        self.current_data = dossier_data
        cover = dossier_data.get("cover_meta", {})
        
        # Populate form
        self.txt_proposed_filename.delete(0, "end")
        self.txt_proposed_filename.insert(0, dossier_data.get("proposed_filename", ""))

        self.txt_book_type.delete(0, "end")
        self.txt_book_type.insert(0, cover.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"))

        self.txt_cover_date.delete(0, "end")
        self.txt_cover_date.insert(0, cover.get("exam_date", ""))

        self.txt_hang.delete(0, "end")
        self.txt_hang.insert(0, cover.get("license_class", "A1"))

        self.txt_khoa.delete(0, "end")
        self.txt_khoa.insert(0, cover.get("course", "25"))

        self.txt_box.delete(0, "end")
        self.txt_box.insert(0, cover.get("box", "48"))

        self.txt_box_number.delete(0, "end")
        self.txt_box_number.insert(0, cover.get("box_number", "115"))

        self.txt_total_gplx.delete(0, "end")
        self.txt_total_gplx.insert(0, str(dossier_data.get("total_citizens", 0)))

        status_note = cover.get("status_note", "Đủ")
        if status_note in ["Đủ", "Ngắt, không theo thứ tự"]:
            self.opt_status_note.set(status_note)
        else:
            self.opt_status_note.set("Ngắt, không theo thứ tự")

        self.txt_seq_summary.delete(0, "end")
        self.txt_seq_summary.insert(0, cover.get("license_sequence", ""))

        # Populate Grid
        self._populate_grid(dossier_data.get("citizens", []))

        # Enable confirmation button now that OCR is complete
        self.btn_confirm.configure(state="normal", fg_color="#1E7E34")

    def _populate_grid(self, citizens: List[Dict[str, Any]]):
        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.citizen_entries = []

        # Table Header
        headers = [("STT", 38), ("Họ và tên", 140), ("Năm sinh", 65), ("Nơi cư trú", 130), ("Số bằng", 95), ("Trang", 45)]
        header_row = ctk.CTkFrame(self.grid_frame, fg_color=("#1F497D", "#1F497D"), corner_radius=2)
        header_row.pack(fill="x", pady=(2, 4))

        for col_name, width in headers:
            lbl = ctk.CTkLabel(header_row, text=col_name, width=width, font=("Segoe UI", 11, "bold"), text_color="white")
            lbl.pack(side="left", padx=2, pady=3)

        # Rows
        for idx, c in enumerate(citizens):
            row_frame = ctk.CTkFrame(self.grid_frame, fg_color=("white", "#2B2B2B") if idx % 2 == 0 else ("#F7F9FB", "#242424"), corner_radius=2)
            row_frame.pack(fill="x", pady=1)

            entry_stt = ctk.CTkEntry(row_frame, width=38, height=24)
            entry_stt.insert(0, str(c.get("stt", idx + 1)))
            entry_stt.pack(side="left", padx=2)

            entry_name = ctk.CTkEntry(row_frame, width=140, height=24)
            entry_name.insert(0, c.get("full_name", ""))
            entry_name.pack(side="left", padx=2)

            entry_birth = ctk.CTkEntry(row_frame, width=65, height=24)
            entry_birth.insert(0, str(c.get("birth_year", "")))
            entry_birth.pack(side="left", padx=2)

            entry_addr = ctk.CTkEntry(row_frame, width=130, height=24)
            entry_addr.insert(0, c.get("address", ""))
            entry_addr.pack(side="left", padx=2)

            # Highlight license number if confidence is low or format is unusual
            entry_lic = ctk.CTkEntry(row_frame, width=95, height=24, font=("Segoe UI", 11, "bold"))
            entry_lic.insert(0, c.get("license_number", ""))
            entry_lic.pack(side="left", padx=2)

            page_num = c.get("page_number", 1)
            btn_page = ctk.CTkButton(
                row_frame,
                text=f"P.{page_num}",
                width=45,
                height=24,
                fg_color=("#4A90E2", "#357ABD"),
                command=lambda p=page_num: self.on_page_jump_callback(p)
            )
            btn_page.pack(side="left", padx=2)

            self.citizen_entries.append({
                "stt": entry_stt,
                "full_name": entry_name,
                "birth_year": entry_birth,
                "address": entry_addr,
                "license_number": entry_lic,
                "page_number": page_num,
                "nationality": c.get("nationality", "Việt Nam")
            })

    def _handle_confirm(self):
        if not self.current_data:
            return

        # Harvest updated values
        final_fn = self.txt_proposed_filename.get().strip()
        cover = self.current_data.get("cover_meta", {})
        cover["book_type"] = self.txt_book_type.get().strip()
        cover["exam_date"] = self.txt_cover_date.get().strip()
        cover["license_class"] = self.txt_hang.get().strip()
        cover["course"] = self.txt_khoa.get().strip()
        cover["box"] = self.txt_box.get().strip()
        cover["box_number"] = self.txt_box_number.get().strip()
        cover["status_note"] = self.opt_status_note.get().strip()
        cover["license_sequence"] = self.txt_seq_summary.get().strip()

        # Harvest citizens
        updated_citizens = []
        for idx, item in enumerate(self.citizen_entries, start=1):
            stt_val = item["stt"].get().strip()
            updated_citizens.append({
                "stt": int(stt_val) if stt_val.isdigit() else idx,
                "full_name": item["full_name"].get().strip(),
                "birth_year": item["birth_year"].get().strip(),
                "address": item["address"].get().strip(),
                "license_number": item["license_number"].get().strip(),
                "nationality": item["nationality"],
                "page_number": item["page_number"]
            })

        self.on_confirm_callback(
            original_path=self.current_data["original_path"],
            final_filename=final_fn,
            cover_meta=cover,
            citizens=updated_citizens
        )
