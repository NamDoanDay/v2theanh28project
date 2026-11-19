"""
PDF Viewer Component for CustomTkinter with Bidirectional (Horizontal & Vertical) Scrolling.
Renders high-resolution pages, supports zooming, rotation, scrollbars, and Shift+Wheel panning.
"""
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Optional
import pypdfium2 as pdfium

class PDFViewerFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.pdf_path: Optional[str] = None
        self.pdf_doc: Optional[pdfium.PdfDocument] = None
        self.total_pages: int = 0
        self.current_page_idx: int = 0
        self.zoom_level: float = 1.0
        self.rotation_angle: int = 0
        self.current_pil_img: Optional[Image.Image] = None
        self.tk_image_ref: Optional[ImageTk.PhotoImage] = None

        self._build_ui()

    def _build_ui(self):
        # 1. Top Toolbar
        self.toolbar = ctk.CTkFrame(self, height=40, fg_color=("gray85", "gray20"))
        self.toolbar.pack(fill="x", padx=4, pady=(4, 2))

        self.btn_prev = ctk.CTkButton(self.toolbar, text="◀ Trang trước", width=95, height=28, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=4, pady=4)

        self.lbl_page = ctk.CTkLabel(self.toolbar, text="Trang 0 / 0", font=("Segoe UI", 12, "bold"))
        self.lbl_page.pack(side="left", padx=10, pady=4)

        self.btn_next = ctk.CTkButton(self.toolbar, text="Trang sau ▶", width=95, height=28, command=self.next_page)
        self.btn_next.pack(side="left", padx=4, pady=4)

        # Zoom & Rotate Controls
        self.btn_zoom_out = ctk.CTkButton(self.toolbar, text="🔍 -", width=45, height=28, command=self.zoom_out)
        self.btn_zoom_out.pack(side="right", padx=3, pady=4)

        self.lbl_zoom = ctk.CTkLabel(self.toolbar, text="100%", font=("Segoe UI", 11))
        self.lbl_zoom.pack(side="right", padx=4, pady=4)

        self.btn_zoom_in = ctk.CTkButton(self.toolbar, text="🔍 +", width=45, height=28, command=self.zoom_in)
        self.btn_zoom_in.pack(side="right", padx=3, pady=4)

        self.btn_rotate = ctk.CTkButton(self.toolbar, text="🔄 Xoay", width=65, height=28, command=self.rotate_page)
        self.btn_rotate.pack(side="right", padx=6, pady=4)

        # 2. Canvas Container with Horizontal & Vertical Scrollbars
        self.canvas_container = ctk.CTkFrame(self, fg_color="transparent")
        self.canvas_container.pack(fill="both", expand=True, padx=4, pady=2)

        # Scrollbars
        self.v_scrollbar = ctk.CTkScrollbar(self.canvas_container, orientation="vertical")
        self.v_scrollbar.pack(side="right", fill="y")

        self.h_scrollbar = ctk.CTkScrollbar(self, orientation="horizontal")
        self.h_scrollbar.pack(fill="x", padx=4, pady=(0, 4))

        # Tkinter Canvas for smooth bidirectional scrolling
        bg_color = "#E5E5E5" if ctk.get_appearance_mode() == "Light" else "#1F1F1F"
        self.canvas = tk.Canvas(
            self.canvas_container,
            bg=bg_color,
            highlightthickness=0,
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.v_scrollbar.configure(command=self.canvas.yview)
        self.h_scrollbar.configure(command=self.canvas.xview)

        # Bind mousewheel events:
        # Standard wheel -> vertical scroll
        # Shift + wheel -> horizontal scroll
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

        # Placeholder message on canvas
        self.placeholder_text = self.canvas.create_text(
            200, 150,
            text="Chưa nạp tệp PDF scan",
            font=("Segoe UI", 13, "italic"),
            fill="gray"
        )

    def _on_mousewheel(self, event):
        if event.state & 0x0001: # Shift key pressed
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_pdf(self, pdf_path: str, initial_page: int = 1):
        self.pdf_path = pdf_path
        try:
            self.pdf_doc = pdfium.PdfDocument(pdf_path)
            self.total_pages = len(self.pdf_doc)
            self.current_page_idx = max(0, min(initial_page - 1, self.total_pages - 1))
            self.rotation_angle = 0
            self.zoom_level = 1.0
            self._render_current_page()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(250, 150, text=f"Lỗi khi đọc file PDF: {e}", fill="red", font=("Segoe UI", 11))

    def _render_current_page(self):
        if not self.pdf_doc or self.total_pages == 0:
            return

        page = self.pdf_doc[self.current_page_idx]
        base_dpi = 150
        scale = (base_dpi / 72.0) * self.zoom_level
        bitmap = page.render(scale=scale)
        pil_img = bitmap.to_pil()

        if self.rotation_angle != 0:
            pil_img = pil_img.rotate(self.rotation_angle, expand=True)

        self.current_pil_img = pil_img

        # Convert to Tkinter PhotoImage
        self.tk_image_ref = ImageTk.PhotoImage(pil_img)

        # Clear canvas and draw image
        self.canvas.delete("all")
        # Draw image centered or at (0, 0)
        img_w, img_h = pil_img.size
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image_ref)

        # Set scrollable region
        self.canvas.config(scrollregion=(0, 0, img_w, img_h))

        # Update labels and button states
        self.lbl_page.configure(text=f"Trang {self.current_page_idx + 1} / {self.total_pages}")
        self.lbl_zoom.configure(text=f"{int(self.zoom_level * 100)}%")
        self.btn_prev.configure(state="normal" if self.current_page_idx > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page_idx < self.total_pages - 1 else "disabled")

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self._render_current_page()

    def next_page(self):
        if self.current_page_idx < self.total_pages - 1:
            self.current_page_idx += 1
            self._render_current_page()

    def go_to_page(self, page_num: int):
        target = max(0, min(page_num - 1, self.total_pages - 1))
        if target != self.current_page_idx:
            self.current_page_idx = target
            self._render_current_page()

    def zoom_in(self):
        if self.zoom_level < 2.5:
            self.zoom_level += 0.2
            self._render_current_page()

    def zoom_out(self):
        if self.zoom_level > 0.4:
            self.zoom_level -= 0.2
            self._render_current_page()

    def rotate_page(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._render_current_page()
