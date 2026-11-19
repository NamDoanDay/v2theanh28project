"""
Main Application Window for GPLX Digitization, Renaming & Verification.
Features Dual-Mode Interface:
Tab 1: 📥 Số hóa & Đổi tên (3-column resizable layout with PanedWindow)
Tab 2: 🔍 Tra cứu Hồ sơ (Sub-millisecond query, 1-click jump to PDF page)
"""
import os
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, Any, Optional

from src.gui.batch_queue import BatchQueueFrame
from src.gui.pdf_viewer import PDFViewerFrame
from src.gui.review_panel import ReviewPanel
from src.gui.search_screen import SearchScreenFrame
from src.gui.lan_screen import LANScreenFrame
from src.pipeline import process_dossier_pdf, commit_dossier
from src.config import DEFAULT_OUTPUT_DIR

class GPLXApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HỆ THỐNG SỐ HÓA, ĐỔI TÊN & TRA CỨU HỒ SƠ GPLX LỊCH SỬ (v2.0)")
        self.geometry("1400x850")
        self.minsize(1200, 700)

        # Set appearance
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.active_file_path: Optional[str] = None
        self.is_processing_batch: bool = False

        self._build_layout()

        # Handle window close to shutdown LAN server gracefully
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Default to Full Screen (Maximized window) on startup
        try:
            self.after(100, lambda: self.state("zoomed"))
        except Exception:
            pass

    def _build_layout(self):
        # Top Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=6)
        self.tabview.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        self.tab_ingest = self.tabview.add("📥 SỐ HÓA & ĐỔI TÊN HỒ SƠ")
        self.tab_search = self.tabview.add("🔍 TRA CỨU HỒ SƠ & MỞ FILE SCAN")
        self.tab_lan = self.tabview.add("🌐 CHIA SẺ MẠNG LAN (MÁY CHỦ NỘI BỘ)")

        self._build_ingest_tab()
        self._build_search_tab()
        self._build_lan_tab()

    def _build_lan_tab(self):
        self.lan_screen = LANScreenFrame(self.tab_lan)
        self.lan_screen.pack(fill="both", expand=True)

    def _build_ingest_tab(self):
        # 3-column split layout using PanedWindow for draggable resizing
        sash_color = "#B0B8C4" if ctk.get_appearance_mode() == "Light" else "#3A3D40"
        self.paned = tk.PanedWindow(
            self.tab_ingest,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=6,
            sashpad=2,
            bg=sash_color,
            bd=0
        )
        self.paned.pack(fill="both", expand=True, padx=2, pady=2)

        # Pane 1: Sidebar Batch Queue
        self.sidebar = BatchQueueFrame(
            self.paned,
            width=280,
            on_select_file_callback=self.on_file_selected,
            on_batch_start_callback=self.on_batch_run_requested
        )
        self.paned.add(self.sidebar, minsize=230, width=280)

        # Pane 2: PDF Viewer with Bidirectional Scrolling
        self.viewer = PDFViewerFrame(self.paned)
        self.paned.add(self.viewer, minsize=380, width=540)

        # Pane 3: Review & Edit Panel
        self.review = ReviewPanel(
            self.paned,
            width=580,
            on_confirm_callback=self.on_confirm_commit,
            on_page_jump_callback=self.on_page_jump
        )
        self.paned.add(self.review, minsize=420, width=580)

    def _build_search_tab(self):
        self.search_screen = SearchScreenFrame(
            self.tab_search,
            on_open_pdf_callback=self.on_search_view_pdf
        )
        self.search_screen.pack(fill="both", expand=True)

    def on_search_view_pdf(self, pdf_path: str, page_num: int):
        """Switches to Ingestion tab and loads the PDF at the specific page."""
        self.tabview.set("📥 SỐ HÓA & ĐỔI TÊN HỒ SƠ")
        self.viewer.load_pdf(pdf_path, initial_page=page_num)

    def on_file_selected(self, file_path: str):
        item = self.sidebar.get_item(file_path)
        if not item:
            return

        self.active_file_path = file_path
        self.viewer.load_pdf(file_path, initial_page=1)

        if item["status"] == "READY" and item["data"]:
            self.review.load_data(item["data"])
        elif item["status"] == "COMPLETED" and item["data"]:
            self.review.load_data(item["data"])
        elif item["status"] == "PENDING":
            # Run OCR in background
            self._process_single_file_async(file_path)

    def _process_single_file_async(self, file_path: str):
        self.sidebar.update_item_status(file_path, "PROCESSING")
        self.sidebar.start_loading()

        def worker():
            prov_code = self.sidebar.get_selected_province_code()
            try:
                res = process_dossier_pdf(file_path, default_province=prov_code)
                self.after(0, lambda: self._on_single_file_processed(file_path, res))
            except Exception as e:
                self.after(0, lambda: self._on_single_file_error(file_path, str(e)))
            finally:
                self.after(0, self.sidebar.stop_loading)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_single_file_processed(self, file_path: str, data: Dict[str, Any]):
        self.sidebar.update_item_status(file_path, "READY", data=data)
        if self.active_file_path == file_path:
            self.review.load_data(data)

    def _on_single_file_error(self, file_path: str, err_msg: str):
        self.sidebar.update_item_status(file_path, "ERROR")
        if self.active_file_path == file_path:
            messagebox.showerror("Lỗi OCR", f"Không thể xử lý file:\n{os.path.basename(file_path)}\n\nChi tiết: {err_msg}")

    def on_batch_run_requested(self, prov_code: str):
        if self.is_processing_batch:
            messagebox.showinfo("Thông báo", "Đang trong tiến trình chạy hàng loạt!")
            return

        pending_items = [it for it in self.sidebar.queue_items if it["status"] == "PENDING"]
        if not pending_items:
            messagebox.showinfo("Thông báo", "Không có tệp nào ở trạng thái Chờ xử lý!")
            return

        self.is_processing_batch = True
        self.sidebar.start_loading()

        def batch_worker():
            for item in pending_items:
                path = item["path"]
                self.after(0, lambda p=path: self.sidebar.update_item_status(p, "PROCESSING"))
                try:
                    res = process_dossier_pdf(path, default_province=prov_code)
                    self.after(0, lambda p=path, d=res: self.sidebar.update_item_status(p, "READY", data=d))
                except Exception as e:
                    self.after(0, lambda p=path: self.sidebar.update_item_status(p, "ERROR"))
            
            self.is_processing_batch = False
            self.after(0, self.sidebar.stop_loading)
            self.after(0, lambda: messagebox.showinfo("Hoàn tất", "Đã xử lý OCR xong toàn bộ hàng đợi! Bắt đầu duyệt từng file."))

        t = threading.Thread(target=batch_worker, daemon=True)
        t.start()

    def on_page_jump(self, page_num: int):
        self.viewer.go_to_page(page_num)

    def on_confirm_commit(self, original_path: str, final_filename: str, cover_meta: Dict[str, Any], citizens: list):
        try:
            # Save directly into the same folder where the file was uploaded
            target_folder = os.path.dirname(os.path.abspath(original_path))
            
            res = commit_dossier(
                original_pdf_path=original_path,
                final_filename=final_filename,
                cover_meta=cover_meta,
                citizens=citizens,
                output_dir=target_folder
            )

            # Update sidebar status
            self.sidebar.update_item_status(original_path, "COMPLETED")

            # Refresh search screen stats & LAN screen stats
            self.search_screen.refresh_stats()
            if hasattr(self, "lan_screen"):
                self.lan_screen.refresh_state()

            # Notification
            msg = (
                f"Đã duyệt và lưu thành công vào đúng thư mục tải lên!\n\n"
                f"• Thư mục lưu: {target_folder}\n"
                f"• PDF chuẩn mới: {os.path.basename(res['pdf_path'])}\n"
                f"• File Excel con: {os.path.basename(res['excel_path'])}\n"
                f"• Cập nhật Sổ theo dõi tỉnh: {os.path.basename(res['master_summary_path'])}\n"
                f"• Tệp gốc ({os.path.basename(original_path)}) vẫn được giữ nguyên toàn vẹn!\n"
                f"• Đồng bộ vào CSDL tìm kiếm: {res['total_citizens']} công dân."
            )
            messagebox.showinfo("Thành công", msg)

            # Automatically select next ready item
            self._select_next_item()

        except Exception as e:
            messagebox.showerror("Lỗi Lưu Hồ Sơ", f"Không thể lưu kết quả:\n{e}")

    def _select_next_item(self):
        for item in self.sidebar.queue_items:
            if item["status"] in ["READY", "PENDING"]:
                self.on_file_selected(item["path"])
                break

    def on_close(self):
        """Gracefully stops LAN server and terminates GUI."""
        try:
            from src.server.lan_server import lan_server
            if lan_server.is_running:
                lan_server.stop()
        except Exception:
            pass
        self.destroy()
