"""
Main Application Window for GPLX Digitization, Renaming & Verification.
Features Dual-Mode Interface:
Tab 1: 📥 Số hóa & Đổi tên (3-column resizable layout with PanedWindow)
Tab 2: 🔍 Tra cứu Hồ sơ (Sub-millisecond query, 1-click jump to PDF page)
"""
import os
import queue
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, Any, Optional

from src.gui.batch_queue import BatchQueueFrame
from src.gui.pdf_viewer import PDFViewerFrame
from src.gui.review_panel import ReviewPanel
from src.gui.search_screen import SearchScreenFrame
from src.gui.lan_screen import LANScreenFrame
from src.pipeline import process_dossier_pdf, commit_dossier, commit_folder_dossier
from src.logger import get_logger, set_exception_notifier

logger = get_logger(__name__)

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
        self.active_item = None
        self.is_processing_batch: bool = False
        self._closing = False
        self._ui_tasks = queue.Queue()
        self._worker_lock = threading.Lock()
        self._active_workers = 0
        self._ocr = ThreadPoolExecutor(max_workers=1, thread_name_prefix="GPLX-OCR")
        set_exception_notifier(
            lambda title, message: self._dispatch_to_ui(self._show_error_popup, title, message)
        )

        self._build_layout()
        self.report_callback_exception = self._report_callback_exception
        self.after(50, self._drain_ui_tasks)

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
            on_batch_start_callback=self.on_batch_run_requested,
            dispatch_to_ui=self._dispatch_to_ui,
            on_worker_start=self._worker_started,
            on_worker_finish=self._worker_finished,
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
            on_page_jump_callback=self.on_page_jump,
            on_skip_callback=self.on_skip_next,
        )
        self.paned.add(self.review, minsize=420, width=580)

    def on_skip_next(self):
        """Advances to the next dossier in queue when skipped."""
        self._select_next_item(after=self.active_item)

    def _build_search_tab(self):
        self.search_screen = SearchScreenFrame(
            self.tab_search,
            on_open_pdf_callback=self.on_search_view_pdf
        )
        self.search_screen.pack(fill="both", expand=True)

    def on_search_view_pdf(self, pdf_path: str, page_num: int):
        """Switches to Ingestion tab and loads the PDF at the specific page."""
        if self.active_file_path != pdf_path:
            self.active_file_path = None
            self.active_item = None
            self.review.clear_data()
        self.tabview.set("📥 SỐ HÓA & ĐỔI TÊN HỒ SƠ")
        self.viewer.load_pdf(pdf_path, initial_page=page_num)

    def _is_active(self, item):
        return self.active_item is item and self.sidebar.get_item(item["path"]) is item

    def on_file_selected(self, file_path: Optional[str]):
        if file_path is None:
            self.active_file_path = None
            self.active_item = None
            self.review.clear_data()
            self.viewer.clear_preview()
            return
        item = self.sidebar.get_item(file_path)
        if not item:
            return

        if self.active_item is not item:
            self.review.clear_data()
        self.active_item = item
        self.active_file_path = file_path
        self.viewer.load_pdf(file_path, initial_page=1)

        if item.get("rename_only") and item["status"] == "COMPLETED":
            name = os.path.basename(item.get("saved_pdf") or file_path)
            self.review.clear_data(f"Đã lưu PDF {name}")
        elif item["status"] in {"READY", "COMPLETED", "SAVING"} and item["data"]:
            self.review.load_data(item["data"])
            if item["status"] == "SAVING":
                self.review.set_saving(True)
        elif item["status"] == "PROCESSING":
            self.review.clear_data("Đang đọc thông tin PDF…")
        elif item["status"] in {"PENDING", "ERROR"}:
            self._process_single_file_async(file_path)

    def _process_single_file_async(self, file_path: str):
        item = self.sidebar.get_item(file_path)
        if not item:
            return
        self.sidebar.update_entry(item, "PROCESSING")
        self.review.clear_data("Đang đọc thông tin PDF…")
        prov_code = self.sidebar.get_selected_province_code()
        rename_only = item.get("rename_only", False)

        def worker():
            try:
                res = process_dossier_pdf(file_path, default_province=prov_code, rename_only=rename_only)
                logger.info("PDF review data ready: %s", file_path)
                self._dispatch_to_ui(self._on_single_file_processed, item, res)
            except Exception as exc:
                logger.exception("OCR failed for %s", file_path)
                self._dispatch_to_ui(self._on_single_file_error, item, str(exc))

        logger.info("Queued PDF review: %s, rename_only=%s", file_path, rename_only)
        try:
            self._launch_worker(worker, ocr=True)
        except Exception:
            self.sidebar.update_entry(item, "ERROR")
            raise

    def _on_single_file_processed(self, item, data: Dict[str, Any]):
        self.sidebar.update_entry(item, "READY", data)
        if self._is_active(item):
            self.review.load_data(data)

    def _on_single_file_error(self, item, err_msg: str):
        self.sidebar.update_entry(item, "ERROR")
        if self._is_active(item):
            self.review.clear_data("Lỗi đọc PDF. Chọn lại file để thử lại.")
            messagebox.showerror("Lỗi OCR", f"Không thể xử lý file:\n{item['filename']}\n\nChi tiết: {err_msg}")

    def on_batch_run_requested(self, prov_code: str):
        if self.sidebar.rename_mode:
            return
        if self.is_processing_batch:
            messagebox.showinfo("Thông báo", "Đang trong tiến trình chạy hàng loạt!")
            return

        pending_items = [it for it in self.sidebar.queue_items if it["status"] == "PENDING"]
        if not pending_items:
            messagebox.showinfo("Thông báo", "Không có tệp nào ở trạng thái Chờ xử lý!")
            return

        self.is_processing_batch = True
        self.sidebar.start_loading()
        for item in pending_items:
            item["status"] = "PROCESSING"
        self.sidebar._render_queue()

        def batch_worker():
            try:
                for item in pending_items:
                    path = item["path"]
                    try:
                        res = process_dossier_pdf(path, default_province=prov_code)
                        self._dispatch_to_ui(self._on_single_file_processed, item, res)
                    except Exception as exc:
                        logger.exception("Batch OCR failed for %s", path)
                        self._dispatch_to_ui(self._on_single_file_error, item, str(exc))
            finally:
                self._dispatch_to_ui(self._finish_batch)

        try:
            self._launch_worker(batch_worker, ocr=True)
        except Exception:
            for item in pending_items:
                item["status"] = "PENDING"
            self._finish_batch(show_dialog=False)
            raise

    def _finish_batch(self, show_dialog=True):
        self.is_processing_batch = False
        self.sidebar.stop_loading()
        self.sidebar._render_queue()
        if show_dialog and not self.sidebar.rename_mode:
            messagebox.showinfo("Hoàn tất", "Đã xử lý OCR xong hàng đợi. Bạn có thể duyệt từng PDF.")

    def on_page_jump(self, page_num: int):
        self.viewer.go_to_page(page_num)

    def on_confirm_commit(self, original_path: str, final_filename: str, cover_meta: Dict[str, Any], citizens: list):
        if item := self.sidebar.get_item(original_path):
            if item.get("rename_only"):
                if self._is_active(item) and item["status"] == "READY":
                    self._save_folder_pdf(item, final_filename, cover_meta)
                return
        try:
            # Save directly into the same folder where the file was uploaded
            target_folder = os.path.dirname(os.path.abspath(original_path))
            data = self.review.current_data or {}
            source = data if data.get("original_path") == original_path else {}
            
            res = commit_dossier(
                original_pdf_path=original_path,
                final_filename=final_filename,
                cover_meta=cover_meta,
                citizens=citizens,
                output_dir=target_folder,
                source_tables=source.get("tables"),
                source_stamp=source.get("source_stamp"),
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
                f"• Tệp gốc ({os.path.basename(original_path)}) được giữ nguyên.\n"
            )
            if res["db_error"]:
                messagebox.showwarning("Đã lưu hồ sơ, lỗi đồng bộ CSDL", msg + f"• Lỗi đồng bộ: {res['db_error']}")
            else:
                messagebox.showinfo("Thành công", msg + f"• Đồng bộ vào CSDL tìm kiếm: {res['total_citizens']} công dân.")

            # Automatically select next ready item
            self._select_next_item()

        except Exception as exc:
            logger.exception("Could not save dossier %s", original_path)
            messagebox.showerror("Lỗi Lưu Hồ Sơ", f"Không thể lưu kết quả:\n{exc}")

    def _save_folder_pdf(self, item, final_filename, cover_meta):
        data = item["data"]
        data["cover_meta"] = cover_meta
        data["review_filename"] = final_filename
        stamp = data["source_stamp"]
        self.sidebar.update_entry(item, "SAVING")
        self.review.set_saving(True)

        def save():
            try:
                result = commit_folder_dossier(item["path"], final_filename, cover_meta, source_stamp=stamp)
            except Exception as exc:
                logger.exception("Folder review save failed for %s", item["path"])
                self._dispatch_to_ui(self._finish_folder_save, item, None, str(exc))
            else:
                self._dispatch_to_ui(self._finish_folder_save, item, result)

        try:
            self._launch_worker(save)
        except Exception as exc:
            logger.exception("Could not start folder save for %s", item["path"])
            self._finish_folder_save(item, None, str(exc))

    def _finish_folder_save(self, item, result, error=None):
        if error:
            self.sidebar.update_entry(item, "READY")
            if self._is_active(item):
                self.review.set_saving(False)
            if self.sidebar.get_item(item["path"]) is item:
                messagebox.showerror("Không thể lưu PDF và sổ tổng hợp", f"{item['filename']}\n\n{error}")
            return
        item["saved_pdf"] = result["pdf_path"]
        self.sidebar.update_entry(item, "COMPLETED")
        if self._is_active(item):
            self.review.clear_data(f"Đã lưu PDF {os.path.basename(result['pdf_path'])}")
            self._select_next_item(after=item)

    def _select_next_item(self, after=None):
        if after is not None:
            items = self.sidebar.queue_items
            index = next(i for i, item in enumerate(items) if item is after)
            for item in items[index + 1:] + items[:index]:
                if item["status"] in {"READY", "PENDING", "PROCESSING"}:
                    self.on_file_selected(item["path"])
                    return
            return
        for item in self.sidebar.queue_items:
            if item["status"] in ["READY", "PENDING"]:
                self.on_file_selected(item["path"])
                break

    def on_close(self):
        """Gracefully stops LAN server and terminates GUI."""
        with self._worker_lock:
            active_workers = self._active_workers
        if active_workers or not self._ui_tasks.empty():
            messagebox.showwarning(
                "Đang xử lý",
                "Vui lòng đợi tác vụ nền hoàn tất rồi đóng ứng dụng để tránh gián đoạn xử lý tệp.",
            )
            return
        self._closing = True
        self._ocr.shutdown(wait=False)
        try:
            from src.server.lan_server import lan_server
            if lan_server.is_running:
                lan_server.stop()
        except Exception:
            logger.exception("Could not stop LAN server cleanly")
        try:
            self.viewer.close_pdf()
        except Exception:
            logger.exception("Could not close the active PDF cleanly")
        self.destroy()

    def _dispatch_to_ui(self, callback, *args, **kwargs):
        if not self._closing:
            self._ui_tasks.put((callback, args, kwargs))

    def _worker_started(self):
        with self._worker_lock:
            self._active_workers += 1

    def _worker_finished(self):
        with self._worker_lock:
            self._active_workers -= 1

    def _launch_worker(self, work, *, ocr=False):
        def run():
            try:
                work()
            finally:
                self._worker_finished()

        self._worker_started()
        try:
            if ocr:
                self._ocr.submit(run)
            else:
                threading.Thread(target=run, daemon=True).start()
        except Exception:
            self._worker_finished()
            raise

    def _drain_ui_tasks(self):
        while not self._ui_tasks.empty():
            callback, args, kwargs = self._ui_tasks.get()
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.exception("UI task callback failed: %r", callback)
                self._show_error_popup(
                    "Lỗi ứng dụng",
                    "Một thao tác giao diện gặp lỗi. Chi tiết đã được ghi vào file log.",
                )
        if not self._closing:
            self.after(50, self._drain_ui_tasks)

    def _report_callback_exception(self, exc_type, exc_value, exc_traceback):
        logger.error(
            "Unhandled Tkinter callback exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        self._show_error_popup(
            "Lỗi ứng dụng",
            "Ứng dụng gặp lỗi khi xử lý thao tác giao diện.\n"
            f"{exc_type.__name__}: {exc_value}\n\nChi tiết đã được ghi vào file log.",
        )

    @staticmethod
    def _show_error_popup(title: str, message: str):
        try:
            messagebox.showerror(title, message)
        except Exception:
            logger.exception("Could not display error popup")
