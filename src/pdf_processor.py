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
    
    for page in pdf:
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        images.append(pil_image)
        
    return images

def get_pdf_page_count(pdf_path: str) -> int:
    """Returns the total number of pages in the PDF."""
    pdf = pdfium.PdfDocument(pdf_path)
    return len(pdf)
