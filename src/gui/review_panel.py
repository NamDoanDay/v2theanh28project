"""
Review & Quick Edit Panel (Right Column).
Displays extracted metadata, proposed filename, sequence analysis, and editable citizen grid.
"""
import customtkinter as ctk
from tkinter import StringVar, messagebox
from typing import Dict, Any, List, Callable, Optional

from src.config import PROVINCE_CODES
from src.cover_parser import DOCUMENT_LABELS
from src.naming_rules import DOSSIER_GROUPS, is_valid_windows_filename_stem, propose_dossier_filename
from src.pipeline import summarize_license_table

class ReviewPanel(ctk.CTkFrame):
    def __init__(self, master, on_confirm_callback: Callable, on_page_jump_callback: Callable, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_confirm_callback = on_confirm_callback
        self.on_page_jump_callback = on_page_jump_callback
        self.current_data: Optional[Dict[str, Any]] = None
        self.citizen_entries: List[Dict[str, Any]] = []
        self.table_options = {}
        self._saving = False
        self.group_fields = {}
        self.naming_fields = {field: StringVar(master=self) for field in (
            "exam_date", "decision_number", "decision_date", "first_license_no", "last_license_no",
        )}
        self.province_options = {f"{p['code']} - {p['name']}": p for p in PROVINCE_CODES}

        self._build_ui()
        for value in self.naming_fields.values():
            value.trace_add("write", self._refresh_naming)

    def _build_ui(self):
        # 1. Top Section: Proposed Filename Banner
        self.banner_frame = ctk.CTkFrame(self, fg_color=("#EBF3FB", "#1F2D3D"), corner_radius=6)
        self.banner_frame.pack(fill="x", padx=6, pady=(6, 4))

        lbl_fn_title = ctk.CTkLabel(self.banner_frame, text="TÊN FILE ĐỀ XUẤT (QUY TẮC LƯU TRỮ):", font=("Segoe UI", 11, "bold"), text_color=("#1F497D", "#5B9BD5"))
        lbl_fn_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.txt_proposed_filename = ctk.CTkEntry(self.banner_frame, font=("Consolas", 13, "bold"), height=32)
        self.txt_proposed_filename.pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_naming = ctk.CTkLabel(self.banner_frame, text="", anchor="w", justify="left", wraplength=380)
        self.lbl_naming.pack(fill="x", padx=10)
        self.btn_metadata_page = ctk.CTkButton(self.banner_frame, text="", height=26)

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
        ctk.CTkLabel(self.card_a, text="Ngày thi/sát hạch:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.txt_cover_date = ctk.CTkEntry(self.card_a, width=120, height=28, textvariable=self.naming_fields["exam_date"])
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

        ctk.CTkLabel(self.card_a, text="Mã tỉnh lưu trữ:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.cmb_province = ctk.CTkComboBox(
            self.card_a, values=list(self.province_options), state="readonly", command=self._on_province_selected,
        )
        self.cmb_province.grid(row=3, column=1, columnspan=3, sticky="ew", padx=8)
        self.chk_province = ctk.CTkCheckBox(self.card_a, text="Xác nhận dùng mã tỉnh đã chọn", command=self._refresh_naming)
        self.chk_province.grid(row=4, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        self.chk_province.grid_remove()

        ctk.CTkLabel(self.card_a, text="Nhóm nếu thiếu ngày thi:").grid(row=5, column=0, sticky="w", padx=8)
        self.cmb_group = ctk.CTkOptionMenu(self.card_a, values=["Tự động", *DOSSIER_GROUPS], command=self._refresh_naming)
        self.cmb_group.grid(row=5, column=1, columnspan=3, sticky="w", padx=8, pady=4)

        for row, (field, label) in enumerate([
            ("decision_number", "Số quyết định"), ("decision_date", "Ngày ký quyết định"),
            ("first_license_no", "Số GPLX đầu"), ("last_license_no", "Số GPLX cuối"),
        ], start=6):
            caption = ctk.CTkLabel(self.card_a, text=label)
            caption.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            entry = ctk.CTkEntry(self.card_a, textvariable=self.naming_fields[field])
            entry.grid(row=row, column=1, columnspan=3, sticky="ew", padx=8, pady=4)
            self.group_fields[field] = (caption, entry)

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
            values=["Đủ", "Ngắt, không theo thứ tự", "Không có dữ liệu", "Cần rà soát"],
            width=170,
            height=28
        )
        self.opt_status_note.grid(row=0, column=3, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(self.card_b, text="Dãy số GPLX:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.txt_seq_summary = ctk.CTkEntry(self.card_b, height=28)
        self.txt_seq_summary.grid(row=1, column=1, columnspan=3, sticky="ew", padx=8, pady=4)
        self.cmb_tables = ctk.CTkOptionMenu(self.card_b, values=["Chọn danh sách GPLX"], command=self._select_table)
        self.cmb_tables.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(4, 2))
        self.cmb_tables.grid_remove()
        self.btn_table_page = ctk.CTkButton(self.card_b, text="", height=26)
        self.btn_table_page.grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 4))
        self.btn_table_page.grid_remove()

        self.card_b.grid_columnconfigure(1, weight=1)
        self.card_b.grid_columnconfigure(3, weight=1)

        # Card C: Editable Citizens Grid
        self.lbl_card_c = ctk.CTkLabel(self.scroll_form, text="DANH SÁCH CÔNG DÂN TRONG SỔ (CLICK DÒNG ĐỂ NHẢY TRANG PDF)", font=("Segoe UI", 12, "bold"))
        self.lbl_card_c.pack(anchor="w", pady=(10, 2))

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
        self.current_data = None
        self._saving = False
        self.txt_proposed_filename.configure(state="normal")
        self._show_form()
        cover = dossier_data.get("cover_meta", {})
        
        # Populate form
        for field, var in self.naming_fields.items():
            var.set(cover.get(field, ""))
        province = next(
            (label for label, item in self.province_options.items() if item["code"] == cover.get("province_code")),
            "Chọn mã tỉnh",
        )
        self.cmb_province.set(province)
        self.cmb_group.set(cover.get("confirmed_group") or "Tự động")
        self.chk_province.deselect()
        if cover.get("province_confirmed"):
            self.chk_province.select()

        self.txt_book_type.delete(0, "end")
        self.txt_book_type.insert(0, cover.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"))

        self.txt_hang.delete(0, "end")
        self.txt_hang.insert(0, cover.get("license_class", "A1"))

        self.txt_khoa.delete(0, "end")
        self.txt_khoa.insert(0, cover.get("course", "25"))

        self.txt_box.delete(0, "end")
        self.txt_box.insert(0, cover.get("box", "48"))

        self.txt_box_number.delete(0, "end")
        self.txt_box_number.insert(0, cover.get("box_number", "115"))

        self.table_options = {}
        for i, table in enumerate(dossier_data.get("tables", []), start=1):
            first = table["rows"][0]["page_number"]
            last = table["rows"][-1]["page_number"]
            pages = f"{first}–{last}" if first != last else str(first)
            self.table_options[f"Danh sách {i} · trang {pages}"] = table
        self.btn_table_page.grid_remove()
        if self.table_options:
            self.cmb_tables.configure(values=list(self.table_options))
            selected = cover.get("selected_table")
            if selected not in self.table_options:
                selected = next(iter(self.table_options)) if len(self.table_options) == 1 else "Chọn danh sách GPLX"
            self.cmb_tables.set(selected)
            self.cmb_tables.grid()
            if selected in self.table_options:
                self._show_table_page(self.table_options[selected])
        else:
            self.cmb_tables.grid_remove()
        self._show_table_summary(cover)

        if dossier_data.get("rename_only"):
            self.lbl_card_c.pack_forget()
            self.grid_frame.pack_forget()
            self._clear_grid()
        else:
            self.lbl_card_c.pack(anchor="w", pady=(10, 2))
            self.grid_frame.pack(fill="both", expand=True, pady=2)
            self._populate_grid(dossier_data.get("citizens", []))

        self.current_data = dossier_data
        self._refresh_naming()
        if draft := dossier_data.get("review_filename"):
            self.txt_proposed_filename.delete(0, "end")
            self.txt_proposed_filename.insert(0, draft)

    def _show_table_summary(self, cover):
        self.txt_total_gplx.delete(0, "end")
        if cover.get("total_licenses") is not None:
            self.txt_total_gplx.insert(0, str(cover["total_licenses"]))
        self.opt_status_note.set(cover.get("status_note") or "Cần rà soát")
        self.txt_seq_summary.delete(0, "end")
        self.txt_seq_summary.insert(0, cover.get("license_sequence", ""))

    def _show_table_page(self, table):
        review_pages = table.get("unresolved_pages", [])
        page = review_pages[0] if review_pages else table["rows"][0]["page_number"]
        text = f"Đối chiếu trang {page}" if review_pages else f"Xem trang {page} của danh sách"
        self.btn_table_page.configure(text=text, command=lambda: self.on_page_jump_callback(page))
        self.btn_table_page.grid()

    def _select_table(self, label):
        if not self.current_data or label not in self.table_options:
            return
        table = self.table_options[label]
        stats = summarize_license_table(table)
        self.current_data["sequence_analysis"] = stats.pop("sequence_analysis")
        cover = self.current_data["cover_meta"]
        cover.update(stats, selected_table=label)
        data = self.current_data
        self.current_data = None
        for field in ("first_license_no", "last_license_no"):
            self.naming_fields[field].set(cover[field])
        self.current_data = data
        self._show_table_summary(cover)
        self._show_table_page(table)
        self._refresh_naming()

    def _needs_table_choice(self, proposal):
        return proposal.group == "SQL" and len(self.table_options) > 1 and self.cmb_tables.get() not in self.table_options

    def _on_province_selected(self, _choice):
        self.chk_province.deselect()
        self._refresh_naming()

    def _naming_inputs(self):
        cover = self.current_data["cover_meta"]
        province = self.province_options.get(self.cmb_province.get(), {})
        return {
            **{field: value.get().strip() for field, value in self.naming_fields.items()},
            "province_code": province.get("code", ""),
            "province_confirmed": bool(self.chk_province.get()),
            "suggested_province_code": cover.get("suggested_province_code", ""),
            "license_column_empty": cover.get("license_column_empty", False),
            "confirmed_group": self.cmb_group.get() if self.cmb_group.get() in DOSSIER_GROUPS else "",
        }

    def _refresh_naming(self, *_, update_filename=True):
        if not self.current_data or self._saving:
            return
        fields = self._naming_inputs()
        suggested = fields["suggested_province_code"]
        if fields["province_code"] and suggested and fields["province_code"] != suggested:
            self.chk_province.grid()
        else:
            self.chk_province.grid_remove()
        self.cmb_group.configure(state="disabled" if fields["exam_date"] else "normal")

        proposal = propose_dossier_filename(**fields)
        needs_table = self._needs_table_choice(proposal)
        if update_filename:
            self.txt_proposed_filename.delete(0, "end")
            if proposal.filename and not needs_table:
                self.txt_proposed_filename.insert(0, proposal.filename)
        rename_only = self.current_data.get("rename_only")
        visible = {
            "decision_number": proposal.group in {None, "QĐTT", "QĐSH"},
            "decision_date": proposal.group in {None, "QĐTT"},
            "first_license_no": proposal.group in {None, "SQL"},
            "last_license_no": proposal.group in {None, "SQL"},
        }
        for field, widgets in self.group_fields.items():
            for widget in widgets:
                if not rename_only or visible[field]:
                    widget.grid()
                else:
                    widget.grid_remove()
        lines = [f"Nhóm hồ sơ {proposal.group}"] if proposal.group else []
        cover = self.current_data["cover_meta"]
        document_label = DOCUMENT_LABELS.get(cover.get("document_type"))
        if document_label:
            lines.append(document_label)
        if suggested:
            lines.append(f"Mã tỉnh OCR gợi ý {suggested}")
        if proposal.errors:
            lines.extend(["Cần rà soát", *proposal.errors.values()])
        if cover.get("table_review"):
            lines.append(cover["table_review"])
        for field, warning in cover.get("metadata_review", {}).items():
            if not fields.get(field) and field not in proposal.errors:
                lines.append(warning)
        self.lbl_naming.configure(text="\n".join(lines))
        page = cover.get("metadata_pages", {}).get("document_type")
        if page:
            self.btn_metadata_page.configure(
                text=f"Xem trang {page} chứa thông tin hồ sơ", command=lambda: self.on_page_jump_callback(page),
            )
            self.btn_metadata_page.pack(anchor="w", padx=10, pady=(0, 6))
        else:
            self.btn_metadata_page.pack_forget()
        self.btn_confirm.configure(
            text="XÁC NHẬN LƯU PDF VÀ SỔ TỔNG HỢP" if rename_only else "✔ XÁC NHẬN: ĐỔI TÊN PDF & XUẤT EXCEL & CẬP NHẬT TỔNG HỢP",
            state="disabled" if proposal.errors or needs_table else "normal",
            fg_color="gray50" if proposal.errors or needs_table else "#1E7E34",
        )

    def _show_form(self):
        self.scroll_form.pack(fill="both", expand=True, padx=6, pady=2, before=self.bottom_bar)

    def set_saving(self, saving):
        self._saving = saving
        self.txt_proposed_filename.configure(state="disabled" if saving else "normal")
        if saving:
            self.scroll_form.pack_forget()
            self.btn_confirm.configure(text="Đang lưu PDF và sổ tổng hợp…", state="disabled", fg_color="gray50")
        else:
            self._show_form()
            self._refresh_naming(update_filename=False)

    def clear_data(self, message="Chọn PDF để xem và rà soát."):
        self.current_data = None
        self._saving = False
        self.txt_proposed_filename.configure(state="normal")
        self.txt_proposed_filename.delete(0, "end")
        self.lbl_naming.configure(text=message)
        self.btn_metadata_page.pack_forget()
        self.cmb_tables.grid_remove()
        self.btn_table_page.grid_remove()
        self.scroll_form.pack_forget()
        self.btn_confirm.configure(text="XÁC NHẬN", state="disabled", fg_color="gray50")

    def _clear_grid(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.citizen_entries = []

    def _populate_grid(self, citizens: List[Dict[str, Any]]):
        self._clear_grid()

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
            if c.get("license_state") in ("uncertain", "unknown_column"):
                entry_lic.configure(placeholder_text="Cần rà soát")
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
        if not self.current_data or self._saving:
            return

        # Harvest updated values
        final_fn = self.txt_proposed_filename.get().strip()
        fields = self._naming_inputs()
        proposal = propose_dossier_filename(**fields)
        if self._needs_table_choice(proposal):
            messagebox.showwarning("Cần rà soát", "Hãy chọn danh sách GPLX dùng để đặt tên.")
            return
        if proposal.errors:
            messagebox.showwarning("Cần rà soát", "\n".join(proposal.errors.values()))
            return
        if not is_valid_windows_filename_stem(final_fn):
            messagebox.showwarning("Tên file không hợp lệ", "Nhập tên file hợp lệ cho Windows và bỏ phần đuôi .pdf.")
            return

        cover = {**self.current_data["cover_meta"], **fields}
        cover["province_name"] = self.province_options[self.cmb_province.get()]["name"]
        cover["dossier_group"] = proposal.group
        cover["book_type"] = self.txt_book_type.get().strip()
        cover["license_class"] = self.txt_hang.get().strip()
        cover["course"] = self.txt_khoa.get().strip()
        cover["box"] = self.txt_box.get().strip()
        cover["box_number"] = self.txt_box_number.get().strip()
        cover["status_note"] = self.opt_status_note.get().strip()
        cover["license_sequence"] = self.txt_seq_summary.get().strip()
        count = self.txt_total_gplx.get().strip()
        if count and not (len(count) <= 12 and count.isascii() and count.isdecimal()):
            messagebox.showwarning("Số lượng không hợp lệ", "Nhập tổng số GPLX bằng số nguyên không âm.")
            return
        cover["total_licenses"] = int(count) if count else None

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
