"""
OCR Engine wrapper for GPLX processing.
Utilizes RapidOCR (PaddleOCR ONNX runtime) for CPU-optimized inference.
"""
import os
import numpy as np
from PIL import Image
from typing import List, Tuple, Any

_OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            # Initialize with default lightweight English/Vietnamese/Chinese models
            _OCR_ENGINE = RapidOCR()
        except ImportError:
            _OCR_ENGINE = None
    return _OCR_ENGINE

def run_ocr(image_or_path: Any) -> Tuple[List[Any], float]:
    """
    Executes OCR on an image (PIL Image, numpy array, or file path).
    Returns (results, elapse_time).
    Each item in results is: [box, text, score]
    """
    engine = get_ocr_engine()
    if engine is None:
        raise RuntimeError("RapidOCR is not yet installed or failed to import.")
    
    if isinstance(image_or_path, Image.Image):
        img_np = np.array(image_or_path.convert('RGB'))
    elif isinstance(image_or_path, str):
        img_pil = Image.open(image_or_path).convert('RGB')
        img_np = np.array(img_pil)
    else:
        img_np = image_or_path
        
    result, elapse = engine(img_np)
    if result is None:
        result = []
        
    return result, elapse
