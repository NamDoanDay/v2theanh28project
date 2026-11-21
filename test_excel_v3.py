import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import openpyxl
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from src.database import DatabaseManager
from src.excel_generator import generate_excel_companion
from src.gui.app import GPLXApp
from src.pipeline import commit_dossier
from src.server import lan_server
from src.table_extractor import table_citizens


def table(columns, rows):
    return {"columns": [{"label": label, "role": role} for label, role in columns], "rows": rows}


def row(cells, page, *, code="", state="blank", bounds=None):
    return {"cells": cells, "page_number": page, "stt": 1, "identity_confident": True,
            "license_number": code, "license_state": state, "bounds": bounds or []}


class ExcelV3Test(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="gplx-xlsx-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.meta = {"province_code": "15", "book_type": "Sổ gốc GPLX", "exam_date": "22/03/1996",
                     "box": "49", "box_number": "116", "license_class": "A1", "course": "26", "total_pages": 2}

    def pdf(self, filename, *, with_media=False, folder=None):
        path = (folder or self.root) / filename
        Image.init()
        with Image.new("RGB", (500, 360), "white") as first, Image.new("RGB", (500, 360), "white") as second:
            if with_media:
                draw = ImageDraw.Draw(second)
                draw.rectangle((55, 65, 135, 155), fill="#3869ab")
                draw.line([(39, 161), (150, 161)], fill="black", width=1)
                draw.line([(330, 95), (353, 119), (385, 88)], fill="black", width=4)
                draw.rectangle((56, 175, 126, 254), fill="#3869ab")  # crosses a cell border
            first.save(path, save_all=True, append_images=[second], resolution=100)
        return path

    def test_dynamic_columns_text_blanks_and_media_are_tied_to_source_cells(self):
        pdf = self.pdf("source.pdf", with_media=True)
        columns = [("Họ và tên", "full_name"), ("Ảnh 3 x 4", "photo"), ("Số TT bảng kê", "register_index"),
                   ("Số giấy phép", "license_number"), ("Ký nhận", "signature"), ("Ngày trả", "return_date")]
        names = ["Nguyễn Văn A", "Nguyễn Văn B"]
        first = row([names[0], "", "000126", "", "", ""], 2,
                    bounds=[None, (.08, .12, .30, .46), None, None, (.59, .12, .85, .46), None])
        second = row([names[1], "", "000127", "", "", "=ABC"], 2,
                     bounds=[None, (.08, .50, .30, .84), None, None, (.59, .50, .85, .84), None])
        narrower = table([("Họ và tên", "full_name"), ("Năm sinh", "birth_year")], [row(["Bùi Văn C", "1979"], 1)])
        tables = [table(columns, [first, second]), narrower]
        citizens = [person for t in tables for person in table_citizens(t)]
        target = self.root / "source.xlsx"
        generate_excel_companion(self.meta, citizens, target, source_tables=tables, pdf_path=str(pdf))
        workbook = openpyxl.load_workbook(target)
        try:
            first_sheet, second_sheet = [sheet for sheet in workbook if sheet.sheet_state == "visible"]
            self.assertEqual([c.value for c in first_sheet[5][:7]], [label for label, _ in columns] + ["Trang PDF"])
            self.assertEqual([c.value for c in second_sheet[5][:3]], ["Họ và tên", "Năm sinh", "Trang PDF"])
            self.assertEqual(first_sheet["C6"].value, "000126")
            self.assertEqual(first_sheet["C6"].data_type, "s")
            self.assertIsNone(first_sheet["D6"].value)
            self.assertEqual(first_sheet["F7"].value, "=ABC")
            self.assertEqual(first_sheet["F7"].data_type, "s")
            self.assertEqual(first_sheet["G6"].value, 2)
            self.assertEqual(second_sheet["C6"].value, 1)
            self.assertEqual({(graphic.anchor._from.col, graphic.anchor._from.row) for graphic in first_sheet._images},
                             {(1, 5), (4, 5)})
            self.assertIn("Cần đối chiếu ảnh", first_sheet["B7"].comment.text)
            self.assertIsNone(first_sheet["E7"].comment)
        finally:
            workbook.close()

    def test_imports_both_formats_keeps_pages_and_reads_visible_workbook_edits(self):
        modern = self.pdf("Mẫu GPLX 50%25.pdf")
        legacy = self.pdf("old.pdf")
        roles = [("Họ và tên", "full_name"), ("Ngày cấp", "issue_date"), ("Mã GPLX", "license_number")]
        sources = [
            table(roles, [row(["Nguyễn Văn A", "01/02/2007", "AP014542"], 2, state="uncertain")]),
            table([("Số TT bảng kê", "register_index"), ("Họ và tên", "full_name")],
                  [row(["00042", "Bùi Văn B"], 1, state="unknown_column")]),
        ]
        people = [c for t in sources for c in table_citizens(t)]
        people[1]["license_number"] = "00000123"  # a reviewed value without a source license column
        generate_excel_companion(self.meta, people, modern.with_suffix(".xlsx"), source_tables=sources)
        generate_excel_companion(self.meta, [{"stt": 7, "full_name": "Phạm Văn C", "license_number": "C244337",
                                              "page_number": 2}], legacy.with_suffix(".xlsx"))
        db = DatabaseManager(str(self.root / "index.db"))
        self.assertEqual(db.reindex_from_directory(self.root), 2)
        self.assertEqual(db.search("00000123")[0]["page_number"], 1)
        self.assertEqual(db.search("C244337")[0]["page_number"], 2)
        self.assertEqual(db.search("AP014542"), [])
        self.assertEqual(db.search("Nguyen Van A")[0]["page_number"], 2)

        workbook = openpyxl.load_workbook(modern.with_suffix(".xlsx"))
        self.assertIn("Cần đối chiếu", workbook.active["C6"].comment.text)
        workbook.active["C6"] = "AP014543"
        workbook.save(modern.with_suffix(".xlsx"))
        workbook.close()
        self.assertEqual(db.reindex_from_directory(self.root), 2)
        modern_record, = db.search("AP014543")
        self.assertEqual(Path(modern_record["pdf_path"]), modern)
        self.assertEqual(modern_record["page_number"], 2)
        self.assertEqual(modern_record["box_number"], "116")
        self.assertEqual(len(db.search("00000123")), 1)

        desktop = SimpleNamespace(active_file_path=None, active_item=None, review=Mock(), tabview=Mock(), viewer=Mock())
        GPLXApp.on_search_view_pdf(desktop, modern_record["pdf_path"], modern_record["page_number"])
        desktop.viewer.load_pdf.assert_called_once_with(str(modern), initial_page=2)
        with patch.object(lan_server, "db_manager", db), TestClient(lan_server.app) as client:
            result = client.get("/api/search", params={"q": "AP014543"}).json()["results"][0]
            self.assertEqual(result["page_number"], 2)
            response = client.get("/api/pdf", params={"path": result["pdf_path"]})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers["content-disposition"].startswith("inline; filename*="))
            self.assertEqual(response.content, modern.read_bytes())
            response = client.get("/api/excel", params={"path": result["excel_path"]})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers["content-disposition"].startswith("attachment; filename*="))

    def test_full_commit_wires_source_table_and_syncs_confirmed_edits(self):
        folder = self.root / "YenBai" / "HOP 49" / "HO SO 116"
        folder.mkdir(parents=True)
        pdf = self.pdf("original.pdf", folder=folder)
        columns = [("Họ và tên", "full_name"), ("Năm sinh", "birth_year"), ("Số bằng", "license_number"),
                   ("Ngày hết hạn", "expiry_date")]
        source = table(columns, [row(["Nguyễn Văn A", "1981", "AP014542", "31/12/2030"], 2, code="AP014542", state="valid")])
        people = table_citizens(source)
        people[0]["license_number"] = "AP014549"
        db = DatabaseManager(str(self.root / "full.db"))
        with patch("src.pipeline.DatabaseManager", return_value=db):
            result = commit_dossier(str(pdf), "15.368.25.09.2015", self.meta, people, source_tables=[source])
        self.assertIsNone(result["db_error"])
        self.assertEqual(db.search("AP014549")[0]["page_number"], 2)
        self.assertEqual(Path(result["pdf_path"]).read_bytes(), pdf.read_bytes())
        workbook = openpyxl.load_workbook(result["excel_path"])
        try:
            self.assertEqual(workbook.active["C6"].value, "AP014549")
            self.assertEqual(workbook.active["D6"].value, "31/12/2030")
            self.assertEqual(workbook.active["E6"].value, 2)
        finally:
            workbook.close()

    def test_invalid_page_and_duplicate_filename_do_not_replace_indexed_record(self):
        original = self.pdf("registered.pdf")
        columns = [("Họ và tên", "full_name"), ("Số GPLX", "license_number")]
        good = table(columns, [row(["Nguyễn Văn A", "AP014542"], 2, code="AP014542", state="valid")])
        generate_excel_companion(self.meta, table_citizens(good), original.with_suffix(".xlsx"), source_tables=[good])
        db = DatabaseManager(str(self.root / "lookup.db"))
        self.assertEqual(db.reindex_from_directory(self.root), 1)

        other = self.root / "different-folder"
        other.mkdir()
        duplicate = self.pdf("registered.pdf", folder=other)
        other_table = table(columns, [row(["Phạm Văn B", "C244337"], 1, code="C244337", state="valid")])
        generate_excel_companion(self.meta, table_citizens(other_table), duplicate.with_suffix(".xlsx"),
                                 source_tables=[other_table])
        errors = []
        with patch("src.database.logger.exception"):
            self.assertEqual(db.reindex_from_directory(other, errors=errors), 0)
        self.assertIn("hồ sơ cùng tên", errors[0][1])
        self.assertEqual(db.search("C244337"), [])

        workbook = openpyxl.load_workbook(original.with_suffix(".xlsx"))
        workbook.active["C6"] = 3
        workbook.save(original.with_suffix(".xlsx"))
        workbook.close()
        errors = []
        with patch("src.database.logger.exception"):
            self.assertEqual(db.reindex_from_directory(self.root, errors=errors), 0)
        self.assertTrue(any("Số trang PDF không hợp lệ" in error for _, error in errors))
        record, = db.search("AP014542")
        self.assertEqual((Path(record["pdf_path"]), record["page_number"]), (original, 2))


if __name__ == "__main__":
    unittest.main()
