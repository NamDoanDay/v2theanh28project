"""
Batch Queue Component (Left Sidebar).
Manages folder loading, queue list, status badges, and province selection.
"""
import os
import customtkinter as ctk
from tkinter import filedialog
from typing import List, Dict, Any, Callable, Optional
from src.config import PROVINCE_CODES, get_default_dulieu_dir

class BatchQueueFrame(ctk.CTkFrame):
    def __init__(self, master, on_select_file_callback: Callable, on_batch_start_callback: Callable, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_select_file_callback = on_select_file_callback
        self.on_batch_start_callback = on_batch_start_callback
        self.queue_items: List[Dict[str, Any]] = []
        self.item_widgets: Dict[str, ctk.CTkFrame] = {}

        # Loading animation state
        self.is_loading: bool = False
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx: int = 0

        self._build_ui()

    def _build_ui(self):
        # 1. Header & Actions
        lbl_title = ctk.CTkLabel(self, text="HÀNG ĐỢI HỒ SƠ", font=("Segoe UI", 13, "bold"))
        lbl_title.pack(anchor="w", padx=10, pady=(8, 4))

        # Province selector
        lbl_prov = ctk.CTkLabel(self, text="Mã Tỉnh / Thành phố:", font=("Segoe UI", 11))
        lbl_prov.pack(anchor="w", padx=10, pady=(2, 0))

        prov_options = [f"{p['code']} - {p['name']}" for p in PROVINCE_CODES]
        self.cmb_province = ctk.CTkComboBox(self, values=prov_options, height=28)
        # Default to 15 - Tỉnh Lào Cai
        for opt in prov_options:
            if opt.startswith("15"):
                self.cmb_province.set(opt)
                break
        self.cmb_province.pack(fill="x", padx=10, pady=(2, 8))

        # Folder button
        self.btn_open_folder = ctk.CTkButton(
            self,
            text="📁 Chọn Thư mục Hồ sơ",
            font=("Segoe UI", 12, "bold"),
            fg_color="#0066CC",
            hover_color="#004C99",
            height=32,
            command=self._choose_folder
        )
        self.btn_open_folder.pack(fill="x", padx=10, pady=3)

        # File button (Prominent emerald color)
        self.btn_open_files = ctk.CTkButton(
            self,
            text="📄 Chọn File PDF lẻ",
            font=("Segoe UI", 11, "bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white",
            height=30,
            command=self._choose_files
        )
        self.btn_open_files.pack(fill="x", padx=10, pady=(2, 4))

        # Folder Batch Copy & Rename button
        self.btn_rename_folder = ctk.CTkButton(
            self,
            text="📑 Đổi tên file (theo folder)",
            font=("Segoe UI", 11, "bold"),
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="white",
            height=30,
            command=self._choose_folder_and_batch_rename
        )
        self.btn_rename_folder.pack(fill="x", padx=10, pady=(2, 6))

        # Progress info
        self.lbl_stats = ctk.CTkLabel(self, text="0 file trong hàng đợi", font=("Segoe UI", 11, "italic"))
        self.lbl_stats.pack(anchor="w", padx=10, pady=2)

        self.progress_bar = ctk.CTkProgressBar(self, height=8)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=10, pady=(2, 8))

        # Run Batch button (Initially disabled until files are uploaded)
        self.btn_run_batch = ctk.CTkButton(
            self,
            text="⚡ Chạy OCR Tự Động",
            font=("Segoe UI", 12, "bold"),
            fg_color="gray50",
            hover_color="#D35400",
            state="disabled",
            height=32,
            command=self._start_batch
        )
        self.btn_run_batch.pack(fill="x", padx=10, pady=(0, 8))

        # 2. Scrollable Queue Item List
        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray12"))
        self.scroll_list.pack(fill="both", expand=True, padx=6, pady=4)

    def get_selected_province_code(self) -> str:
        val = self.cmb_province.get().strip()
        if "-" in val:
            return val.split("-")[0].strip()
        return "15"

    def _choose_folder(self):
        folder = filedialog.askdirectory(
            title="Chọn thư mục chứa các file scan PDF",
            initialdir=get_default_dulieu_dir()
        )
        if folder:
            self._scan_and_populate_folder(folder)

    def _choose_files(self):
        files = filedialog.askopenfilenames(
            title="Chọn các file PDF scan",
            filetypes=[("PDF Files", "*.pdf")],
            initialdir=get_default_dulieu_dir()
        )
        if files:
            self._add_files_to_queue(list(files))

    def _choose_folder_and_batch_rename(self):
        folder = filedialog.askdirectory(
            title="Chọn thư mục chứa các file PDF scan cần đổi tên",
            initialdir=get_default_dulieu_dir()
        )
        if not folder:
            return

        prov_code = self.get_selected_province_code()

        # Disable button during processing
        self.btn_rename_folder.configure(state="disabled", text="⏳ Đang đổi tên...")
        self.progress_bar.set(0)
        self.lbl_stats.configure(text="Đang quét thư mục...")

        def worker():
            from src.pipeline import batch_copy_and_rename_folder_pdfs
            try:
                def on_progress(current, total, filename):
                    pct = current / total if total > 0 else 0
                    self.after(0, lambda: self._update_batch_rename_progress(current, total, filename, pct))

                res = batch_copy_and_rename_folder_pdfs(folder, default_province=prov_code, progress_callback=on_progress)
                self.after(0, lambda: self._on_batch_rename_complete(folder, res))
            except Exception as e:
                from tkinter import messagebox
                self.after(0, lambda: messagebox.showerror("Lỗi Đổi Tên", f"Quá trình đổi tên theo folder gặp lỗi:\n{e}"))
            finally:
                self.after(0, lambda: self.btn_rename_folder.configure(state="normal", text="📑 Đổi tên file (theo folder)"))

        import threading
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _update_batch_rename_progress(self, current: int, total: int, filename: str, pct: float):
        self.progress_bar.set(pct)
        self.lbl_stats.configure(text=f"Đang xử lý {current}/{total}: {filename[:16]}...")

    def _on_batch_rename_complete(self, folder: str, res: Dict[str, Any]):
        from tkinter import messagebox
        self.progress_bar.set(1.0)
        self.lbl_stats.configure(text=f"Đổi tên xong: {res['success_count']}/{res['total_scanned']} file")
        msg = (
            f"Đã hoàn thành Đổi tên file (theo folder)!\n\n"
            f"• Thư mục: {folder}\n"
            f"• Tổng số file PDF scan: {res['total_scanned']}\n"
            f"• Số file đã copy & đổi tên chuẩn: {res['success_count']}\n"
            f"• Lỗi / Bỏ qua: {res['failed_count']}\n\n"
            f"Tất cả các file scan gốc cũ vẫn được giữ nguyên vẹn 100%!"
        )
        messagebox.showinfo("Hoàn Tất Đổi Tên", msg)

    def _scan_and_populate_folder(self, folder_path: str):
        pdf_paths = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdf_paths.append(os.path.join(root, f))
        self._add_files_to_queue(pdf_paths)

    def _add_files_to_queue(self, paths: List[str]):
        for p in paths:
            # Check duplicate
            if any(item["path"] == p for item in self.queue_items):
                continue
            item = {
                "path": p,
                "filename": os.path.basename(p),
                "status": "PENDING", # PENDING, PROCESSING, READY, COMPLETED, ERROR
                "data": None
            }
            self.queue_items.append(item)

        self._render_queue()
        
        # Enable OCR batch button if there are items in queue
        if len(self.queue_items) > 0:
            self.btn_run_batch.configure(state="normal", fg_color="#E67E22")
        else:
            self.btn_run_batch.configure(state="disabled", fg_color="gray50")

    def _render_queue(self):
        # Clear existing
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
        self.item_widgets.clear()

        total = len(self.queue_items)
        done_count = sum(1 for item in self.queue_items if item["status"] == "COMPLETED")
        self.lbl_stats.configure(text=f"Đã duyệt: {done_count} / {total} file")
        self.progress_bar.set(done_count / total if total > 0 else 0)

        for item in self.queue_items:
            path = item["path"]
            fn = item["filename"]
            st = item["status"]

            f_card = ctk.CTkFrame(self.scroll_list, fg_color=("white", "#262626"), corner_radius=4)
            f_card.pack(fill="x", padx=2, pady=2)

            # Status Badge Icon
            badge_map = {
                "PENDING": ("⏳ Chờ", "gray50"),
                "PROCESSING": ("⚙️ OCR...", "#2980B9"),
                "READY": ("👁️ Duyệt", "#27AE60"),
                "COMPLETED": ("✅ Xong", "#2ECC71"),
                "ERROR": ("❌ Lỗi", "#E74C3C")
            }
            badge_text, badge_color = badge_map.get(st, ("Chờ", "gray50"))

            lbl_badge = ctk.CTkLabel(f_card, text=badge_text, text_color=badge_color, font=("Segoe UI", 10, "bold"), width=55)
            lbl_badge.pack(side="left", padx=4, pady=4)

            # Name button (click to select)
            btn_name = ctk.CTkButton(
                f_card,
                text=fn[:22] + "..." if len(fn) > 25 else fn,
                font=("Segoe UI", 11),
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray30"),
                text_color=("black", "white"),
                height=26,
                command=lambda p=path: self.on_select_file_callback(p)
            )
            btn_name.pack(side="left", fill="x", expand=True, padx=2)

            self.item_widgets[path] = f_card

    def update_item_status(self, path: str, new_status: str, data: Optional[Dict[str, Any]] = None):
        for item in self.queue_items:
            if item["path"] == path:
                item["status"] = new_status
                if data:
                    item["data"] = data
                break
        self._render_queue()
        
        # Enable OCR batch button if there are items in queue
        if len(self.queue_items) > 0:
            self.btn_run_batch.configure(state="normal", fg_color="#E67E22")
        else:
            self.btn_run_batch.configure(state="disabled", fg_color="gray50")

    def get_item(self, path: str) -> Optional[Dict[str, Any]]:
        for item in self.queue_items:
            if item["path"] == path:
                return item
        return None

    def start_loading(self):
        """Starts the rotating circle loading indicator on the OCR button."""
        self.is_loading = True
        self.btn_run_batch.configure(state="disabled", fg_color="#C0392B")
        self._animate_spinner()

    def _animate_spinner(self):
        if not self.is_loading:
            return
        frame = self.spinner_frames[self.spinner_idx % len(self.spinner_frames)]
        self.spinner_idx += 1
        self.btn_run_batch.configure(text=f"{frame}  Đang Chạy OCR...")
        self.after(90, self._animate_spinner)

    def stop_loading(self):
        """Stops the loading indicator and restores standard state."""
        self.is_loading = False
        if len(self.queue_items) > 0:
            self.btn_run_batch.configure(text="⚡ Chạy OCR Tự Động", state="normal", fg_color="#E67E22")
        else:
            self.btn_run_batch.configure(text="⚡ Chạy OCR Tự Động", state="disabled", fg_color="gray50")

    def _start_batch(self):
        prov_code = self.get_selected_province_code()
        self.on_batch_start_callback(prov_code)
