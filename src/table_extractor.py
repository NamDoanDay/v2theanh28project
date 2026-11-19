"""
Table extractor and column mapper for GPLX registers.
Maps OCR bounding boxes into structured tabular records:
STT, Họ và tên, Năm sinh, Quốc tịch, Nơi cư trú, Số bằng, Ký nhận.
"""
import re
from typing import List, Dict, Any, Tuple
from src.naming_rules import normalize_license_code
from src.vietnamese_utils import restore_vietnamese_name, normalize_vietnamese_address, normalize_nationality

def assign_column_by_x_ratio(x_ratio: float) -> str:
    """
    Maps horizontal coordinate (ratio 0.0 - 1.0) to corresponding column.
    Based on standard Sổ gốc GPLX layout.
    """
    if x_ratio < 0.08:
        return "stt"
    elif x_ratio < 0.28:
        return "full_name"
    elif x_ratio < 0.38:
        return "photo"
    elif x_ratio < 0.48:
        return "birth_year"
    elif x_ratio < 0.58:
        return "nationality"
    elif x_ratio < 0.80:
        return "address"
    elif x_ratio < 0.92:
        return "license_number"
    else:
        return "signature"

def cluster_boxes_into_rows(ocr_results: List[Any], img_width: int, img_height: int) -> List[Dict[str, Any]]:
    """
    Clusters OCR bounding boxes into distinct citizen rows.
    ocr_results is a list of [box, text, score] from RapidOCR.
    """
    if not ocr_results:
        return []

    # Filter out header texts (TRANG 1, STT, HỌ VÀ TÊN, etc.)
    header_keywords = ["trang", "stt", "họ và tên", "ảnh 3 x 4", "năm sinh", "quốc tịch", "nơi cư trú", "số bằng", "ký nhận"]
    
    data_boxes = []
    for item in ocr_results:
        box, text, score = item[0], str(item[1]).strip(), float(item[2])
        if not text:
            continue
            
        text_lower = text.lower()
        if any(hk in text_lower for hk in header_keywords) and len(text_lower) < 20:
            continue
            
        # Calculate center point
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        center_x = sum(xs) / 4.0
        center_y = sum(ys) / 4.0
        box_height = max(ys) - min(ys)
        
        data_boxes.append({
            "text": text,
            "score": score,
            "center_x": center_x,
            "center_y": center_y,
            "box_height": box_height,
            "x_ratio": center_x / img_width,
            "y_ratio": center_y / img_height
        })

    # Sort vertically from top to bottom
    data_boxes.sort(key=lambda b: b["center_y"])
    
    # Cluster into rows using vertical distance threshold (e.g. ~4% of image height)
    row_clusters: List[List[Dict[str, Any]]] = []
    y_threshold = img_height * 0.05
    
    for b in data_boxes:
        placed = False
        for cluster in row_clusters:
            # Check average Y of the cluster
            avg_y = sum(item["center_y"] for item in cluster) / len(cluster)
            if abs(b["center_y"] - avg_y) < y_threshold:
                cluster.append(b)
                placed = True
                break
        if not placed:
            row_clusters.append([b])

    # Convert clusters into citizen records
    citizens: List[Dict[str, Any]] = []
    
    for row_idx, cluster in enumerate(row_clusters, start=1):
        # Sort left to right
        cluster.sort(key=lambda b: b["center_x"])
        
        row_dict = {
            "stt": None,
            "stt_from_ocr": False,
            "full_name": "",
            "birth_year": "",
            "nationality": "Việt Nam",
            "address": "",
            "license_number": "",
            "confidence": 1.0,
            "raw_items": []
        }
        
        scores = []
        for b in cluster:
            col = assign_column_by_x_ratio(b["x_ratio"])
            scores.append(b["score"])
            row_dict["raw_items"].append((col, b["text"], b["score"]))
            
            if col == "stt":
                digits = re.findall(r"\d+", b["text"])
                if digits:
                    row_dict["stt"] = int(digits[0])
                    row_dict["stt_from_ocr"] = True
                else:
                    t = b["text"].strip()
                    if t in ["I", "l", "|", "!", "i", "/"]:
                        row_dict["stt"] = 1
                        row_dict["stt_from_ocr"] = True
            elif col == "full_name":
                if not row_dict["full_name"]:
                    row_dict["full_name"] = b["text"]
                else:
                    row_dict["full_name"] += " " + b["text"]
            elif col == "birth_year":
                num = re.sub(r"[^0-9]", "", b["text"])
                if len(num) == 4:
                    row_dict["birth_year"] = num
            elif col == "nationality":
                if b["text"] not in ['"', "''"]:
                    row_dict["nationality"] = b["text"]
            elif col == "address":
                if not row_dict["address"]:
                    row_dict["address"] = b["text"]
                else:
                    row_dict["address"] += " " + b["text"]
            elif col == "license_number":
                row_dict["license_number"] = normalize_license_code(b["text"])
        
        # Heuristic rescue: if license_number is still empty, look through all texts in row for pattern
        if not row_dict["license_number"]:
            for b in cluster:
                # E.g. A161541, C244138
                match = re.search(r"([A-Za-z]{1,2}\s*[0-9]{5,7})", b["text"])
                if match:
                    row_dict["license_number"] = normalize_license_code(match.group(1))
                    break

        # Check if this row is actually a table header row
        full_name_upper = row_dict["full_name"].upper().replace(" ", "")
        header_triggers = ["HOVATEN", "HỌVÀTÊN", "NOICUTRU", "NƠICƯTRÚ", "SOBANG", "SỐBẰNG", "NAMSINH", "NĂMSINH", "KYNHAN"]
        is_header_row = any(ht in full_name_upper for ht in header_triggers)
        if "SOBANG" in row_dict["license_number"].upper() or "KYNHAN" in row_dict["license_number"].upper():
            is_header_row = True

        if is_header_row:
            continue

        # Check if STT was merged into the beginning of full_name (e.g. "1. Trần Văn Yên" or "02 - Nguyễn Văn Thủy")
        if not row_dict.get("stt_from_ocr") and row_dict["full_name"]:
            m = re.match(r"^(\d{1,4})[\.\s\-\/\:\)]+\s*(.*)$", row_dict["full_name"])
            if m:
                row_dict["stt"] = int(m.group(1))
                row_dict["stt_from_ocr"] = True
                row_dict["full_name"] = m.group(2).strip()

        # Clean stray OCR artifacts from front of full_name (e.g. '|', '!', 'I ')
        row_dict["full_name"] = re.sub(r"^[I\|l\!\:\.\-\–]\s*", "", row_dict["full_name"]).strip()

        if scores:
            row_dict["confidence"] = round(sum(scores) / len(scores), 2)
            
        # Only add if has a valid name or license number (and not a header)
        if row_dict["full_name"] or (row_dict["license_number"] and row_dict["license_number"] != "UNKNOWN"):
            # Restore full Vietnamese accents for name, address, and nationality
            row_dict["full_name"] = restore_vietnamese_name(row_dict["full_name"])
            row_dict["address"] = normalize_vietnamese_address(row_dict["address"])
            row_dict["nationality"] = normalize_nationality(row_dict["nationality"])
            citizens.append(row_dict)
            
    # Retain exact STT from OCR; do not reset sequentially per page
    return citizens
