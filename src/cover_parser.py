"""Recognize the opening page and extract fields used to name GPLX dossiers."""
import re
import unicodedata
from datetime import date

from src.config import PROVINCE_CODES, find_province_code_by_text

DOCUMENT_LABELS = {
    "cover": "Sổ gốc cấp bằng lái xe cơ giới đường bộ",
    "decision": "Quyết định",
    "decision_with_list": "Hồ sơ quyết định kèm danh sách cấp GPLX",
    "unknown": "",
}
_DECISION_TITLE = re.compile(r"(?m)^[ \t]*quyet[ .\t]*dinh[ \t:.\-]*$")
_COVER_TITLE = re.compile(r"\bso[ .\t]*goc\b|(?m:^[ \t]*cap[ \t]+bang[ \t]+lai[ \t]*xe\b)")
_LIST_TITLE = re.compile(
    r"(?m)^[ \t]*danh[ \t]+sach[^\n]{0,110}(?:trung[ \t]*tuyen|cap[ \t]+giay[ \t]*phep|gplx)"
)
_CITATION_START = re.compile(r"(?m)^[ \t]*(?:can[ \t]+c|xet[ \t]+bien[ \t]+ban)")
_OWN_NUMBER_LABEL = r"(?m)^[ \t]*s[o06](?:[ \t]*:[ \t]*|[ \t]+)"
_ATTACHED_DECISION_LABEL = r"\bkem\s+theo\s+(?:quyet\s*dinh|qd)[ \t]+s[o06][ \t]*:?[ \t]*"
_DECISION_NUMBER = r"([0-9]+)(?:[ \t]*/[ \t]*(q[dđ](?:[a-z0-9]+)?(?:[ \t]*[-_–/][ \t]*[a-z0-9đ]+)*))?"
_DATE_VALUE = (
    r"(?<![0-9])([0-9]{1,2})"
    r"(?:[ \t]*[-/.]+[ \t]*|\s+thang\s*)"
    r"([0-9]{1,2})(?:[ \t]*[-/.]+[ \t]*|\s+nam\s*)([0-9]{4})(?![0-9])"
)
_EXAM_LABEL = r"\b(?:ngay\s+(?:thi|sat\s*hach)|(?:thi|sat\s*hach)\s+ngay)[ \t:.\-]*"


def _fold(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d").replace("Đ", "d"))
        if not unicodedata.combining(c)
    )


def _read_date(text, label):
    dates = set()
    for match in re.finditer(label + _DATE_VALUE, text):
        day, month, year = map(int, match.groups())
        try:
            dates.add(date(year, month, day))
        except ValueError:
            continue
    return dates.pop() if len(dates) == 1 else None


def _format_date(value):
    return f"{value.day:02d}-{value.month:02d}-{value.year:04d}" if value else ""


def _decision_number(text, label):
    # Keep the full suffix. The filename rule only uses the numeric prefix.
    match = re.search(
        label + _DECISION_NUMBER + r"(?=[ \t]*(?:[,;\t]|$|\n|\bngay\b))", text, re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return ""
    number, suffix = match.groups()
    if not suffix:
        return number
    suffix = re.sub(r"[ \t]+", "", suffix.upper())
    return f"{number}/QĐ{suffix[2:]}"


def parse_cover_page_text(
    ocr_text: str, *, header_text: str | None = None, page_number: int = 1,
    uncertain_decision_number: bool = False,
) -> dict:
    """Use header context for the decision and explicit labels for the exam date."""
    raw = unicodedata.normalize("NFC", ocr_text).replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    full_text = _fold(raw)
    header = _fold(unicodedata.normalize("NFC", header_text)) if header_text is not None else full_text
    header = _CITATION_START.split(header, maxsplit=1)[0]
    title = _DECISION_TITLE.search(header)
    preamble = header[:title.start()] if title else header
    has_list = bool(_LIST_TITLE.search(header)) or (
        bool(title) and "ho va ten" in full_text and bool(re.search(r"\bso\s+(?:gplx|bang|giay\s*phep)\b", full_text))
    )
    if has_list:
        document_type = "decision_with_list"
    elif title or re.search(_OWN_NUMBER_LABEL + r"[0-9]+[ \t]*/[ \t]*qd", preamble):
        document_type = "decision"
    elif _COVER_TITLE.search(full_text):
        document_type = "cover"
    else:
        document_type = "unknown"

    exam = _read_date(full_text, _EXAM_LABEL + r"\s*")
    decision_number = ""
    signed = None
    review = {}
    if document_type == "unknown":
        review["document_type"] = "Chưa nhận diện được loại tài liệu."
    if document_type in ("decision", "decision_with_list"):
        attachment = re.search(_ATTACHED_DECISION_LABEL + r"[^\n]*", header) if has_list else None
        if re.search(_OWN_NUMBER_LABEL, preamble) and (title or not attachment):
            decision_number = _decision_number(preamble, _OWN_NUMBER_LABEL)
            # Decisions put the date next to the locality in the header.
            signed = _read_date(preamble, r"(?:^|[,;\t\n])\s*(?:[a-z ]+,\s*)?ngay[ \t]*")
        elif attachment:
            decision_number = _decision_number(attachment[0], _ATTACHED_DECISION_LABEL)
            signed = _read_date(attachment[0], r"\bngay[ \t]*")
        if uncertain_decision_number:
            decision_number = ""
        if not decision_number:
            review["decision_number"] = "Số quyết định chưa đọc rõ."
        if not signed:
            review["decision_date"] = "Ngày ký quyết định chưa đọc rõ."
    if not exam:
        review["exam_date"] = "Ngày thi/sát hạch chưa đọc rõ hoặc có nhiều ngày khác nhau."

    # Restrict province suggestions to the issuing office and the document header.
    issuer_lines = [
        line for line in header.splitlines()
        if re.search(r"\b(?:ubnd|so\s+giao\s+thong|cong\s+an|phong\s+van\s+tai)\b", line)
    ]
    province_code = find_province_code_by_text(" ".join(issuer_lines))
    if not province_code and document_type in ("cover", "unknown"):
        province_code = find_province_code_by_text(header.split("dia diem", 1)[0])
    elif not province_code and has_list and (attached := re.search(_ATTACHED_DECISION_LABEL + r"[^\n]*", header)):
        province_code = find_province_code_by_text(attached[0])
    if not province_code:
        review["province_code"] = "Chưa nhận diện được tỉnh trên tài liệu."

    hang = re.search(r"\bhang[ \t.:]*([a-f](?:[1-4il]|e)?)(?![a-z0-9])", full_text)
    khoa = re.search(r"\bkhoa[ \t.:]+([a-z]?[0-9]{1,5})\b", full_text)
    if not khoa and document_type == "cover":
        khoa = re.search(r"(?m)^[ \t]*k[ \t]*([0-9]{1,5})[ \t.]*$", full_text)
    location = re.search(r"(?im)đ[ịi]a\s*đi[ểe]m\s*(?:thi)?\s*[:.]?\s*([^\n]+)", raw)
    fields = {
        "document_type": document_type,
        "book_type": DOCUMENT_LABELS[document_type],
        "province_code": province_code,
        "province_name": next((p["name"] for p in PROVINCE_CODES if p["code"] == province_code), ""),
        "exam_date": _format_date(exam),
        "decision_date": _format_date(signed),
        "decision_number": decision_number,
        "license_class": hang[1].upper().replace("L", "1").replace("I", "1") if hang else "",
        "course": khoa[1].upper() if khoa else "",
        "exam_location": location[1].strip() if location else "",
        "day": f"{exam.day:02d}" if exam else "",
        "month": f"{exam.month:02d}" if exam else "",
        "year": f"{exam.year:04d}" if exam else "",
        "raw_text": raw,
    }
    fields["metadata_review"] = review
    fields["metadata_pages"] = {
        field: page_number for field in (
            "document_type", "province_code", "exam_date", "decision_number", "decision_date", "license_class", "course",
        ) if fields[field] or field in review
    }
    return fields


def parse_cover_ocr(ocr_results, page_height: int, *, page_number: int = 1) -> dict:
    """Rejoin boxes on the same visual line and isolate the top of the page."""
    lines = []
    boxes = sorted(
        (sum(y for _, y in box) / len(box), min(x for x, _ in box), str(text).strip(), float(score))
        for box, text, score in ocr_results
    )
    for y, x, text, score in boxes:
        if not lines or y - lines[-1][0] > page_height * 0.016:
            lines.append((y, []))
        lines[-1][1].append((x, text, score))

    full_lines, header_lines = [], []
    uncertain_decision_number = False
    for y, parts in lines:
        ordered = sorted(parts)
        row = " ".join(text for _, text, _ in ordered)
        full_lines.append(row)
        if y <= page_height * 0.35:
            # Separate widely spaced header boxes so number and date stay distinct.
            header_lines.append("\t".join(text for _, text, _ in ordered))
            uncertain_decision_number |= any(
                score < 0.80 and bool(re.match(_OWN_NUMBER_LABEL, _fold(text)))
                for _, text, score in ordered
            )

    full_text = "\n".join(full_lines)
    header = "\n".join(header_lines)
    # Cover titles can sit halfway down the page and the issuer can be above them.
    if _COVER_TITLE.search(_fold(full_text)) and not _DECISION_TITLE.search(_fold(header)):
        header = full_text
    return parse_cover_page_text(
        full_text, header_text=header, page_number=page_number,
        uncertain_decision_number=uncertain_decision_number,
    )
