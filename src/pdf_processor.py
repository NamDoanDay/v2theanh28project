"""
PDF processing module: Extract images from PDF pages and manage page rendering.
Uses pypdfium2 and PIL for high-speed, high-resolution rendering without external dependencies.
"""
import os
from typing import List
from PIL import Image
import pypdfium2 as pdfium

def render_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[Image.Image]:
    """
    Renders all pages of a PDF into PIL Image objects.
    Default dpi=200 provides ideal balance between OCR accuracy and processing speed.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    pdf = pdfium.PdfDocument(pdf_path)
    images = []
    scale = dpi / 72.0  # 72 is standard PDF points per inch
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                bitmap = page.render(scale=scale)
                try:
                    images.append(bitmap.to_pil())
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        pdf.close()
    return images

def get_pdf_page_count(pdf_path: str) -> int:
    """Returns the total number of pages in the PDF."""
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        return len(pdf)
    finally:
        pdf.close()

def render_specific_pdf_pages(pdf_path: str, page_indices: List[int], dpi: int = 200) -> dict:
    """
    Renders only the requested page indices (0-based) from a PDF.
    Saves massive CPU time and memory by skipping unneeded intermediate pages.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    pdf = pdfium.PdfDocument(pdf_path)
    rendered = {}
    try:
        total_pages = len(pdf)
        scale = dpi / 72.0
        for idx in page_indices:
            if 0 <= idx < total_pages:
                page = pdf[idx]
                try:
                    bitmap = page.render(scale=scale)
                    try:
                        rendered[idx] = bitmap.to_pil()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
    finally:
        pdf.close()
    return rendered
