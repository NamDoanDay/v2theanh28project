import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from src.pipeline import fast_extract_rename_metadata, summarize_license_table
from src.table_extractor import LicenseTableExtractor, measure_page_grid


SIZE = (900, 730)
EDGES = (25, 90, 255, 375, 550, 720, 875)
HEADERS = ("STT", "Họ và tên", "Năm sinh", "Nơi cư trú", "Số GPLX", "Ngày cấp")


def make_page(*sections, edges=EDGES):
    image = Image.new("L", SIZE, 255)
    draw = ImageDraw.Draw(image)
    result = []
    for start, headers, records in sections:
        values = ([headers] if headers else []) + records
        end = start + 38 * len(values)
        for x in edges:
            draw.line((x, start, x, end), fill=0, width=1)
        for i in range(len(values) + 1):
            y = start + i * 38
            draw.line((edges[0], y, edges[-1], y), fill=0, width=1)
        for i, row in enumerate(values):
            y = start + i * 38 + 9
            for column, value in enumerate(row):
                if value is None:
                    continue
                x = edges[column] + 8
                score = .95
                if isinstance(value, tuple):
                    value, score = value
                if score is None:
                    # A real ink mark that was missed entirely by OCR.
                    draw.rectangle((x, y, x + 5, y + 12), fill=0)
                    continue
                width = min(len(value) * 7, edges[column+1] - x - 5)
                result.append(([(x, y), (x + width, y), (x + width, y + 16), (x, y + 16)], value, score))
    return result, measure_page_grid(image)


def row(stt, code):
    return (str(stt), "Nguyễn Văn A", "1982", "Tỉnh Yên Bái", code, "01/06/2010")


class LicenseTablesV3Test(unittest.TestCase):
    def setUp(self):
        self.extractor = LicenseTableExtractor()

    def read(self, page_number, *sections):
        ocr, grid = make_page(*sections)
        self.extractor.read_page(ocr, SIZE, grid, page_number)

    def test_ignores_fees_and_keeps_first_page_list(self):
        self.read(1, (60, HEADERS, [row(1, "AP014542"), row(3, "AP014544")]),
                  (300, ("Số TT", "Nội dung", "Số lượng", "Phí sát hạch", "Thành tiền", ""),
                   [("1", "Lệ phí cấp GPLX", "29", "50.000", "1.450.000", None)]))
        table, = self.extractor.tables
        self.assertEqual([c["label"] for c in table["columns"]], list(HEADERS))
        self.assertEqual([r["stt"] for r in table["rows"]], [1, 3])
        self.assertEqual([r["page_number"] for r in table["rows"]], [1, 1])

    def test_joins_headerless_and_repeated_header_pages_using_row_order(self):
        self.read(2, (60, HEADERS, [row(1, "C244344"), row(2, "C244355")]))
        self.read(3, (90, None, [row(4, "C244340"), row(6, "C244337")]))
        self.read(4, (80, HEADERS, [row(7, "C244341")]))
        table, = self.extractor.tables
        self.assertEqual([r["page_number"] for r in table["rows"]], [2, 2, 3, 3, 4])
        summary = summarize_license_table(table)
        self.assertEqual((summary["first_license_no"], summary["last_license_no"]), ("C244344", "C244341"))
        self.assertEqual(summary["total_licenses"], 5)

    def test_independent_lists_stay_separate_on_one_page_and_across_pages(self):
        self.read(1, (50, HEADERS, [row(1, "A465211"), row(2, "A465212")]),
                  (350, HEADERS, [row(1, "B295726"), row(2, "B295727")]))
        self.read(2, (50, HEADERS, [row(1, "C244337")]))
        self.assertEqual([t["rows"][0]["license_number"] for t in self.extractor.tables],
                         ["A465211", "B295726", "C244337"])

    def test_side_by_side_lists_stay_separate(self):
        left = (12, 43, 115, 172, 252, 334, 418)
        right = tuple(x + 452 for x in left)
        left_ocr, left_grid = make_page((60, HEADERS, [row(1, "A465211")]), edges=left)
        right_ocr, right_grid = make_page((60, HEADERS, [row(1, "B295726")]), edges=right)
        left_grid.vertical.extend(right_grid.vertical)
        left_grid.horizontal.extend(right_grid.horizontal)
        self.extractor.read_page(left_ocr + right_ocr, SIZE, left_grid, 1)
        self.assertEqual([t["rows"][0]["license_number"] for t in self.extractor.tables],
                         ["A465211", "B295726"])

    def test_follows_matching_license_codes_when_stt_was_not_read(self):
        self.read(1, (60, HEADERS, [row(1, "AP014542"), (None, *row(2, "AP014543")[1:])]))
        self.read(2, (90, None, [(None, *row(3, "AP014544")[1:])]))
        table, = self.extractor.tables
        self.assertEqual([r["license_number"] for r in table["rows"]], ["AP014542", "AP014543", "AP014544"])
        self.assertEqual(table["rows"][-1]["page_number"], 2)

    def test_unresolved_continuation_does_not_use_previous_endpoint(self):
        self.read(1, (60, HEADERS, [row(1, "AP014542"), row(2, "AP014543")]))
        self.read(2, (90, None, [(None, *row(3, "APO14544")[1:])]))
        table, = self.extractor.tables
        summary = summarize_license_table(table)
        self.assertEqual(table["unresolved_pages"], [2])
        self.assertIsNone(summary["total_licenses"])
        self.assertEqual(summary["last_license_no"], "")

    def test_verified_blank_ignores_register_number(self):
        headers = ("STT", "Họ và tên", "Năm sinh", "Số TT bảng kê", "Số giấy phép", "Ngày cấp")
        self.read(1, (60, headers, [
            ("1", "Nguyễn Văn A", "1982", "AP014542", None, "01/06/2010"),
            ("2", "Nguyễn Văn B", "1985", "AP014543", None, "01/06/2010"),
        ]))
        table, = self.extractor.tables
        self.assertEqual([r["license_state"] for r in table["rows"]], ["blank", "blank"])
        self.assertTrue(summarize_license_table(table)["license_column_empty"])
        self.assertEqual(table["rows"][0]["cells"][3:5], ["AP014542", ""])

    def test_register_number_preserves_row_when_ocr_joins_name_and_misses_stt(self):
        headers = ("STT", "Họ và tên", "Năm sinh", "Số TT bảng kê", "Số giấy phép", "Ngày cấp")
        self.read(1, (60, headers, [
            ("1", "Nguyễn Văn A", "1982", "170656", None, "01/06/2010"),
            (None, "HàVũ", "1989", "170657", None, "01/06/2010"),
            ("3", "Nguyễn Văn B", "1985", "170658", None, "01/06/2010"),
        ]))
        table, = self.extractor.tables
        self.assertEqual([r["cells"][3] for r in table["rows"]], ["170656", "170657", "170658"])
        middle = table["rows"][1]
        self.assertIsNone(middle["stt"])
        self.assertFalse(middle["identity_confident"])
        self.assertEqual(middle["cells"][1], "HàVũ")
        self.assertEqual(middle["license_state"], "blank")

    def test_known_license_column_and_birth_year_preserve_row_without_recognized_name(self):
        self.read(1, (60, HEADERS, [
            row(1, "AP014542"),
            (None, "HàVũ", "1989", "Tỉnh Yên Bái", "AP014543", "01/06/2010"),
            row(3, "AP014544"),
            (None, None, None, None, "AP014545", None),
        ]))
        table, = self.extractor.tables
        self.assertEqual([r["license_number"] for r in table["rows"]], ["AP014542", "AP014543", "AP014544"])
        self.assertFalse(table["rows"][1]["identity_confident"])

    def test_ink_and_low_confidence_are_not_verified_blank(self):
        self.read(1, (60, HEADERS, [
            row(1, ("AP014542", .45)), row(2, ("OCR missed", None)), row(3, "AP014544"),
        ]))
        table, = self.extractor.tables
        self.assertEqual([r["license_state"] for r in table["rows"]], ["uncertain", "uncertain", "valid"])
        stats = summarize_license_table(table)
        self.assertEqual((stats["first_license_no"], stats["last_license_no"]), ("", "AP014544"))
        self.assertEqual(stats["license_sequence"], "")
        self.assertFalse(stats["license_column_empty"])

    def test_unknown_header_uses_repeated_pattern_in_one_column(self):
        headers = (*HEADERS[:4], "Ký hiệu", HEADERS[5])
        self.read(1, (60, headers, [row(1, "AH515361"), row(2, "AH515362")]))
        table, = self.extractor.tables
        self.assertTrue(table["columns"][4]["inferred"])
        self.assertEqual([r["license_number"] for r in table["rows"]], ["AH515361", "AH515362"])

    def test_single_match_under_unknown_header_does_not_assign_license_column(self):
        headers = (*HEADERS[:4], "Ký hiệu", HEADERS[5])
        self.read(1, (60, headers, [row(1, "AH515361"), row(2, "163913")]))
        table, = self.extractor.tables
        self.assertEqual([r["license_state"] for r in table["rows"]], ["unknown_column", "unknown_column"])

    def test_folder_naming_requires_a_choice_for_multiple_sql_lists(self):
        self.read(1, (50, HEADERS, [row(1, "A465211")]), (350, HEADERS, [row(1, "B295726")]))
        cover = dict(document_type="cover", exam_date="01/06/2010", province_code="15", decision_date="",
                     decision_number="", metadata_review={})
        with (patch("src.pipeline._pdf_cache_key", return_value=("example.pdf", 5, 5)),
              patch("src.pipeline._cached_opening", return_value=(cover, 1, None)),
              patch("src.pipeline._cached_tables", return_value=self.extractor.tables)):
            with self.assertRaisesRegex(ValueError, "Có nhiều danh sách GPLX"):
                fast_extract_rename_metadata("example.pdf", "15")


if __name__ == "__main__":
    unittest.main()
