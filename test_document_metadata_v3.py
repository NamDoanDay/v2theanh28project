import unittest
from unittest.mock import patch

from src.cover_parser import parse_cover_ocr, parse_cover_page_text
from src.pipeline import _read_opening_page


DECISION = """UBND TỈNH YÊN BÁI
Số: 368/QĐ-SGTVT
Yên Bái, ngày 25 tháng 9 năm 2015
QUYẾT ĐỊNH
Căn cứ Quyết định số 1422/QĐ-UBND ngày 22/09/2009
Căn cứ biên bản và kết quả sát hạch ngày 15/09/2015
Điều 1. Công nhận trúng tuyển hạng A1 khóa P59
"""


class DocumentMetadataV3Test(unittest.TestCase):
    def test_cover_and_field_provenance(self):
        result = parse_cover_page_text(
            "SỞ GIAO THÔNG VẬN TẢI YÊN BÁI\nSỔ GỐC\nHẠNG: A1  KHÓA: 26\nNGÀY THI: 29 - 03 - 1996",
            page_number=2,
        )
        self.assertEqual(result["document_type"], "cover")
        self.assertEqual(result["exam_date"], "29-03-1996")
        self.assertEqual(result["license_class"], "A1")
        self.assertEqual(result["course"], "26")
        self.assertEqual(result["metadata_pages"]["exam_date"], 2)

    def test_decision_keeps_exam_and_signed_dates_separate(self):
        result = parse_cover_page_text(DECISION)
        self.assertEqual(result["document_type"], "decision")
        self.assertEqual(result["exam_date"], "15-09-2015")
        self.assertEqual(result["decision_date"], "25-09-2015")
        self.assertEqual(result["decision_number"], "368/QĐ-SGTVT")
        self.assertEqual(result["province_code"], "15")
        self.assertEqual(result["metadata_review"], {})

    def test_citation_does_not_supply_missing_signed_date(self):
        result = parse_cover_page_text(DECISION.replace("Yên Bái, ngày 25 tháng 9 năm 2015\n", ""))
        self.assertEqual(result["decision_date"], "")
        self.assertIn("decision_date", result["metadata_review"])
        self.assertEqual(result["exam_date"], "15-09-2015")

    def test_attached_list_with_incomplete_year(self):
        result = parse_cover_page_text(
            "DANH SÁCH THÍ SINH TRÚNG TUYỂN ĐƯỢC CẤP GIẤY PHÉP LÁI XE\n"
            "Hạng A1 Ngày thi: 10/06/2010\n"
            "Kèm theo QĐ số: 71/QĐ-SGTVT, ngày 16 tháng 6 năm 200 của Sở GTVT Yên Bái\n"
        )
        self.assertEqual(result["document_type"], "decision_with_list")
        self.assertEqual(result["decision_number"], "71/QĐ-SGTVT")
        self.assertEqual(result["exam_date"], "10-06-2010")
        self.assertEqual(result["decision_date"], "")
        self.assertIn("decision_date", result["metadata_review"])

    def test_low_confidence_decision_number_goes_to_review(self):
        def box(x, y, text, score=0.94):
            return ([(x, y), (x + 20, y), (x + 20, y + 8), (x, y + 8)], text, score)

        boxes = [
            box(100, 55, "UBND TỈNH YÊN BÁI"),
            box(100, 130, "S6: 11 /QD- SGTVT", 0.78),
            box(450, 131, "Yên Bái, ngày 16 tháng 6 năm 2010"),
            box(300, 160, "QUYET DINH"),
            box(110, 400, "Xét biên bản và kết quả sát hạch ngày 10 tháng 6 năm 2010"),
        ]
        result = parse_cover_ocr(boxes[::-1], 1000)
        self.assertEqual(result["document_type"], "decision")
        self.assertEqual(result["decision_number"], "")
        self.assertIn("decision_number", result["metadata_review"])
        self.assertEqual(result["decision_date"], "16-06-2010")
        self.assertEqual(result["exam_date"], "10-06-2010")

    def test_usable_text_layer_needs_no_ocr_for_metadata(self):
        with patch("src.pipeline.read_pdf_page_text", return_value=DECISION), patch("src.pipeline._read_page_ocr") as ocr:
            result, opening_ocr = _read_opening_page(object())
        self.assertEqual(result["decision_number"], "368/QĐ-SGTVT")
        self.assertIsNone(opening_ocr)
        ocr.assert_not_called()


if __name__ == "__main__":
    unittest.main()
