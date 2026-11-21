"""PDFium helpers shared by the OCR worker and the preview."""
from contextlib import closing, contextmanager
from threading import Lock

import pypdfium2 as pdfium


# The preview and OCR worker may use PDFium concurrently, even on different PDFs.
PDFIUM_LOCK = Lock()


@contextmanager
def open_pdf(pdf_path: str):
    with PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(pdf_path)
    try:
        yield pdf
    finally:
        with PDFIUM_LOCK:
            pdf.close()


def page_count(pdf) -> int:
    with PDFIUM_LOCK:
        return len(pdf)


def read_pdf_page_text(pdf, index: int) -> str:
    with PDFIUM_LOCK, closing(pdf[index]) as page, closing(page.get_textpage()) as text_page:
        return text_page.get_text_bounded()


def render_pdf_page(pdf, index: int, dpi: float = 200):
    with PDFIUM_LOCK, closing(pdf[index]) as page, closing(page.render(scale=dpi / 72.0)) as bitmap:
        # Some PIL modes share the bitmap's native buffer.
        return bitmap.to_pil().copy()


def render_pdf_to_images(pdf_path: str, dpi: int = 200) -> list:
    with open_pdf(pdf_path) as pdf:
        return [render_pdf_page(pdf, index, dpi) for index in range(page_count(pdf))]


def get_pdf_page_count(pdf_path: str) -> int:
    with open_pdf(pdf_path) as pdf:
        return page_count(pdf)


def render_specific_pdf_pages(pdf_path: str, page_indices: list[int], dpi: int = 200) -> dict:
    with open_pdf(pdf_path) as pdf:
        total = page_count(pdf)
        return {index: render_pdf_page(pdf, index, dpi) for index in page_indices if 0 <= index < total}
