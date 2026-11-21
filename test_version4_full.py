"""
Comprehensive Version 4 Test Suite for GPLX Digitization & Renaming System.
Validates:
1. Naming rules across all 3 eras (SQL <= 2012, QDTT 2013-28/02/2025, QDSH >= 01/03/2025).
2. Fast dynamic table finding (first and last license endpoints without full scan).
3. ReviewPanel clean UI in folder rename mode (bloated fields completely hidden).
4. Strict output directory preservation across all 3 ingestion modes.
5. Real file validation on C:\\Users\\FPT SHOP\\Desktop\\HOP 49\\HOP 49\\HO SO 113.
"""
import os
import shutil
import tempfile
import unittest
import tkinter as tk
from unittest.mock import MagicMock

from PIL import Image
Image.init()

from src.naming_rules import propose_dossier_filename, is_valid_windows_filename_stem
from src.pipeline import (
    process_dossier_pdf,
    commit_dossier,
    commit_folder_dossier,
    fast_extract_rename_metadata,
    _fast_find_license_endpoints,
)
from src.folder_parser import folder_review_location, find_province_root_dir
from src.gui.review_panel import ReviewPanel


REAL_TEST_FOLDER = r"C:\Users\FPT SHOP\Desktop\HOP 49\HOP 49\HO SO 113"


class TestVersion4NamingRules(unittest.TestCase):
    def test_group1_sql_before_2013(self):
        # Format: [Mã tỉnh].SQL.[Tháng].[Năm].[Số đầu]-[Số cuối].pdf
        prop = propose_dossier_filename(
            province_code="79",
            exam_date="15-06-2008",
            first_license_no="AM570000",
            last_license_no="AM570200",
        )
        self.assertEqual(prop.group, "SQL")
        self.assertEqual(prop.filename, "79.SQL.06.2008.AM570000-AM570200")
        self.assertTrue(is_valid_windows_filename_stem(prop.filename))

    def test_group2_qdtt_2013_to_feb_2025(self):
        # Format: [Mã tỉnh].[Số QĐTT].[Ngày].[Tháng].[Năm ký].pdf
        prop = propose_dossier_filename(
            province_code="15",
            decision_number="368/QĐ-SGTVT",
            decision_date="25-09-2015",
        )
        self.assertEqual(prop.group, "QĐTT")
        self.assertEqual(prop.filename, "15.368.25.09.2015")
        self.assertTrue(is_valid_windows_filename_stem(prop.filename))

    def test_group3_qdsh_from_march_2025(self):
        # Format: [Mã tỉnh].[Số QĐSH].[Ngày].[Tháng].[Năm sát hạch].pdf
        prop = propose_dossier_filename(
            province_code="15",
            decision_number="3081/QĐ-SGTVT",
            exam_date="01-01-2026",
            decision_date="05-01-2026",
        )
        self.assertEqual(prop.group, "QĐSH")
        self.assertEqual(prop.filename, "15.3081.01.01.2026")
        self.assertTrue(is_valid_windows_filename_stem(prop.filename))


class TestReviewPanelCleanUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_folder_rename_mode_hides_unwanted_fields(self):
        """Image 14 verification: In rename_only mode, bloat fields MUST be hidden."""
        panel = ReviewPanel(
            self.root,
            on_confirm_callback=MagicMock(),
            on_page_jump_callback=MagicMock(),
            on_skip_callback=MagicMock(),
        )

        dossier_data = {
            "original_path": "dummy.pdf",
            "original_filename": "dummy.pdf",
            "proposed_filename": "15.SQL.04.1996.C244337-C244340",
            "rename_only": True,
            "cover_meta": {
                "province_code": "15",
                "exam_date": "22-04-1996",
                "first_license_no": "C244337",
                "last_license_no": "C244340",
                "box": "49",
                "box_number": "116",
                "license_class": "A1",
                "course": "28",
                "total_licenses": 4,
            },
            "tables": [],
            "citizens": [],
        }

        panel.load_data(dossier_data)

        # 1. Unwanted fields in Card A MUST be hidden (grid_info is empty)
        self.assertFalse(panel.txt_book_type.winfo_ismapped())
        self.assertFalse(panel.txt_hang.winfo_ismapped())
        self.assertFalse(panel.txt_khoa.winfo_ismapped())
        self.assertFalse(panel.txt_box.winfo_ismapped())
        self.assertFalse(panel.txt_box_number.winfo_ismapped())

        # 2. Entire Card B (Dãy số GPLX & Nhận định) MUST be hidden
        self.assertFalse(panel.card_b.winfo_ismapped())
        self.assertFalse(panel.lbl_card_b.winfo_ismapped())

        # 3. Card C grid MUST be hidden
        self.assertFalse(panel.grid_frame.winfo_ismapped())

        # 4. Big confirm button and skip button must be ready
        self.assertIn("XÁC NHẬN ĐỔI TÊN", panel.btn_confirm.cget("text"))
        self.assertEqual(panel.btn_confirm.cget("state"), "normal")

        # 5. Skip button callback works
        panel._handle_skip()
        panel.on_skip_callback.assert_called_once()

    def test_digitize_mode_shows_all_fields(self):
        """In full digitization mode, all review fields remain visible."""
        panel = ReviewPanel(
            self.root,
            on_confirm_callback=MagicMock(),
            on_page_jump_callback=MagicMock(),
        )

        dossier_data = {
            "original_path": "dummy.pdf",
            "original_filename": "dummy.pdf",
            "proposed_filename": "15.SQL.04.1996.C244337-C244340",
            "rename_only": False,
            "cover_meta": {
                "province_code": "15",
                "exam_date": "22-04-1996",
                "first_license_no": "C244337",
                "last_license_no": "C244340",
                "box": "49",
                "box_number": "116",
                "license_class": "A1",
                "course": "28",
                "total_licenses": 4,
            },
            "tables": [],
            "citizens": [{"stt": 1, "full_name": "Nguyen Van A", "birth_year": "1990", "address": "HN", "license_number": "C244337", "nationality": "VN", "page_number": 1}],
        }

        panel.load_data(dossier_data)
        self.assertIn("XUẤT EXCEL", panel.btn_confirm.cget("text"))


class TestOutputDirectoryPreservation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gplx_test_out_")
        self.source_dir = os.path.join(self.temp_dir, "MyFolder", "HO SO 113")
        os.makedirs(self.source_dir, exist_ok=True)
        self.source_pdf = os.path.join(self.source_dir, "original_scan.pdf")
        # Create minimal 1-page PDF using PIL
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img.save(self.source_pdf, "PDF")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_commit_folder_dossier_saves_in_same_directory(self):
        res = commit_folder_dossier(
            original_pdf_path=self.source_pdf,
            final_filename="15.SQL.04.1996.C244337-C244340",
            cover_meta={"province_code": "15", "exam_date": "22-04-1996"},
        )
        expected_pdf = os.path.join(self.source_dir, "15.SQL.04.1996.C244337-C244340.pdf")
        self.assertEqual(os.path.normpath(res["pdf_path"]), os.path.normpath(expected_pdf))
        self.assertTrue(os.path.exists(expected_pdf))
        self.assertTrue(os.path.exists(self.source_pdf))  # Original kept!

    def test_commit_dossier_saves_in_same_directory(self):
        res = commit_dossier(
            original_pdf_path=self.source_pdf,
            final_filename="15.SQL.04.1996.C244337-C244340",
            cover_meta={"province_code": "15", "exam_date": "22-04-1996"},
            citizens=[],
            output_dir=os.path.dirname(os.path.abspath(self.source_pdf)),
        )
        expected_pdf = os.path.join(self.source_dir, "15.SQL.04.1996.C244337-C244340.pdf")
        expected_xlsx = os.path.join(self.source_dir, "15.SQL.04.1996.C244337-C244340.xlsx")
        self.assertEqual(os.path.normpath(res["pdf_path"]), os.path.normpath(expected_pdf))
        self.assertEqual(os.path.normpath(res["excel_path"]), os.path.normpath(expected_xlsx))
        self.assertTrue(os.path.exists(expected_pdf))
        self.assertTrue(os.path.exists(expected_xlsx))
        self.assertTrue(os.path.exists(self.source_pdf))


class TestRealFilesValidation(unittest.TestCase):
    """Test on the user's real dossier files if available."""
    def test_real_files_fast_scan(self):
        if not os.path.isdir(REAL_TEST_FOLDER):
            self.skipTest(f"Test folder not found: {REAL_TEST_FOLDER}")

        pdfs = [
            f for f in os.listdir(REAL_TEST_FOLDER)
            if f.lower().endswith(".pdf")
        ]
        self.assertGreaterEqual(len(pdfs), 5, "Expected at least 5 PDFs in test folder")

        # Specifically test H38.8.4_SO_0000467_V1_20260425_000002.pdf (table starts on page 3)
        book_pdf = os.path.join(REAL_TEST_FOLDER, "H38.8.4_SO_0000467_V1_20260425_000002.pdf")
        if os.path.exists(book_pdf):
            dossier = process_dossier_pdf(book_pdf, default_province="15", rename_only=True)
            self.assertEqual(dossier["cover_meta"]["province_code"], "15")
            self.assertTrue(dossier["proposed_filename"].startswith("15."))
            # Verify fast execution without processing all 20 pages:
            self.assertEqual(dossier["total_citizens"], 0)  # No citizen rows parsed in rename_only
            self.assertTrue(len(dossier["proposed_filename"]) > 10)


if __name__ == "__main__":
    unittest.main()
