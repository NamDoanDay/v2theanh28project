import ctypes
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import openpyxl

from src.folder_parser import folder_review_location
from src.gui.app import GPLXApp
from src.gui.batch_queue import BatchQueueFrame
from src.gui.review_panel import ReviewPanel
from src.master_summary import read_rename_records, update_or_append_summary_entry
from src.naming_rules import propose_dossier_filename
from src.pipeline import _pdf_cache_key, commit_folder_dossier, list_folder_review_pdfs, process_dossier_pdf


@contextmanager
def lock_workbook(path):
    if os.name != "nt":
        with patch("src.master_summary.os.replace", side_effect=PermissionError("Workbook locked")):
            yield
        return

    from ctypes import wintypes

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    open_file = api.CreateFileW
    open_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    open_file.restype = wintypes.HANDLE
    # Allow reading while preventing replacement of the open workbook.
    handle = open_file(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        api.CloseHandle(wintypes.HANDLE(handle))


class FolderReviewV3Test(unittest.TestCase):
    def setUp(self):
        work = TemporaryDirectory(prefix="gplx-review-")
        self.addCleanup(work.cleanup)
        self.province = Path(work.name) / "DuLieuSoHoa_GPLS" / "Tỉnh Yên Bái"
        self.folder = self.province / "HOP 49" / "HO SO 116"
        self.folder.mkdir(parents=True)
        self.summary = self.province / "So_Theo_Doi_Day_So_GPLX_15.xlsx"
        self.cover = {"province_code": "15", "exam_date": "01/05/2010", "box": "49", "box_number": "116"}

    def source(self, filename="scan.pdf", content=b"original"):
        pdf = self.folder / filename
        pdf.write_bytes(content)
        return pdf

    def test_three_groups_save_adjacent_pdf_and_update_same_province_workbook(self):
        cases = (
            ({"exam_date": "01/05/2010", "first_license_no": "A465211", "last_license_no": "A465212"},
             "15.SQL.05.2010.A465211-A465212"),
            ({"exam_date": "15/09/2015", "decision_number": "368/QĐ-SGTVT", "decision_date": "25/09/2015"},
             "15.368.25.09.2015"),
            ({"exam_date": "04/03/2025", "decision_number": "3081"}, "15.3081.04.03.2025"),
        )
        for i, (fields, expected) in enumerate(cases):
            with self.subTest(name=expected):
                source = self.source(f"scan-{i}.pdf", bytes([i]))
                proposal = propose_dossier_filename(province_code="15", **fields)
                self.assertEqual(proposal.filename, expected)
                cover = {**self.cover, **fields, "dossier_group": proposal.group, "total_licenses": i + 1}
                result = commit_folder_dossier(source, proposal.filename, cover)
                self.assertEqual(Path(result["pdf_path"]).parent.resolve(), source.parent.resolve())
                self.assertEqual(Path(result["pdf_path"]).read_bytes(), bytes([i]))
                self.assertEqual(source.read_bytes(), bytes([i]))
                self.assertEqual(Path(result["master_summary_path"]).resolve(), self.summary.resolve())
        self.assertEqual(list(self.folder.glob("*.xlsx")), [])
        workbook = openpyxl.load_workbook(self.summary)
        try:
            self.assertEqual([workbook.active.cell(r, 4).value for r in (3, 4, 5)], [name for _, name in cases])
            self.assertEqual(workbook.active["C4"].value, "25/09/2015")
            self.assertEqual(workbook.active["H5"].value, 3)
            self.assertEqual(workbook["_GPLX_Rename"].sheet_state, "hidden")
        finally:
            workbook.close()

    def test_real_lock_rolls_back_new_pdf_and_retry_is_idempotent(self):
        source = self.source()
        update_or_append_summary_entry(self.summary, {"pdf_filename": "older", "total_licenses": 99})
        workbook = openpyxl.load_workbook(self.summary)
        workbook.active["N3"] = "=H3*2"
        workbook.active["D3"].style = "Title"
        workbook.save(self.summary)
        workbook.close()
        before = self.summary.read_bytes()
        with lock_workbook(self.summary):
            with self.assertRaisesRegex(PermissionError, "đóng sổ trong Excel"):
                commit_folder_dossier(source, "custom-name", self.cover)
        self.assertEqual(self.summary.read_bytes(), before)
        self.assertEqual(source.read_bytes(), b"original")
        self.assertFalse((self.folder / "custom-name.pdf").exists())
        self.assertEqual(list(self.province.glob(".gplx-*")), [])
        for _ in range(2):
            commit_folder_dossier(source, "custom-name", self.cover)
        workbook = openpyxl.load_workbook(self.summary)
        try:
            self.assertEqual(workbook.active.max_row, 4)
            self.assertEqual(workbook.active["H3"].value, 99)
            self.assertEqual(workbook.active["N3"].value, "=H3*2")
            self.assertEqual(workbook.active["D3"].style, "Title")
            self.assertEqual(len(read_rename_records(workbook)), 1)
        finally:
            workbook.close()
        self.assertEqual(list_folder_review_pdfs(self.folder), [
            (str(source.resolve()), str((self.folder / "custom-name.pdf").resolve())),
        ])

    def test_matching_bytes_are_insufficient_without_source_record(self):
        source = self.source("first.pdf")
        different_source = self.source("second.pdf")
        self.source("unknown-copy.pdf")
        with self.assertRaises(FileExistsError):
            commit_folder_dossier(source, "unknown-copy", self.cover)
        commit_folder_dossier(source, "chosen", self.cover)
        with self.assertRaises(FileExistsError):
            commit_folder_dossier(different_source, "chosen", self.cover)
        self.assertEqual(different_source.read_bytes(), b"original")

    def test_source_changes_after_ocr_are_detected(self):
        source = self.source()
        stamp = _pdf_cache_key(source)[1:]
        source.write_bytes(b"replacement PDF file")
        with self.assertRaisesRegex(ValueError, "PDF gốc đã thay đổi"):
            commit_folder_dossier(source, "chosen", self.cover, source_stamp=stamp)
        self.assertFalse(self.summary.exists())

    def test_folder_review_prepares_metadata_without_citizen_projection(self):
        source = self.source()
        with (patch("src.pipeline._cached_opening", return_value=({"province_code": "15", "exam_date": "01/05/2010"}, 1, None)),
              patch("src.pipeline._cached_tables", return_value=[{"rows": [{"identity_confident": True,
                    "license_state": "valid", "license_number": "A465211"}]}]),
              patch("src.pipeline.table_citizens") as project_rows):
            data = process_dossier_pdf(str(source), "15", rename_only=True)
        project_rows.assert_not_called()
        self.assertEqual(data["citizens"], [])
        self.assertEqual(data["cover_meta"]["box_number"], "116")
        self.assertEqual(data["proposed_filename"], "15.SQL.05.2010.A465211-A465211")
        self.assertEqual(Path(folder_review_location(source)["province_root"]).resolve(), self.province.resolve())


class FolderReviewControllerTest(unittest.TestCase):
    def test_scan_switches_to_review_queue_and_opens_first_pending(self):
        token = object()
        panel = SimpleNamespace(
            _folder_scan=token, rename_mode=False, btn_rename_folder=Mock(), lbl_title=Mock(),
            btn_run_batch=Mock(), _render_queue=Mock(), on_select_file_callback=Mock(), queue_items=[],
        )
        BatchQueueFrame._finish_folder_scan(panel, token, [("a.pdf", "saved.pdf"), ("b.pdf", None)])
        self.assertTrue(panel.rename_mode)
        self.assertEqual([item["status"] for item in panel.queue_items], ["COMPLETED", "PENDING"])
        panel.on_select_file_callback.assert_called_once_with("b.pdf")

    def test_late_ocr_for_old_entry_with_same_path_does_not_load_panel(self):
        new_item = {"path": "same.pdf", "rename_only": True}
        old_item = {"path": "same.pdf", "rename_only": False}
        app = SimpleNamespace(active_item=new_item, review=Mock(),
                              sidebar=SimpleNamespace(get_item=lambda path: new_item, update_entry=Mock()))
        app._is_active = lambda item: GPLXApp._is_active(app, item)
        GPLXApp._on_single_file_processed(app, old_item, {"cover_meta": {}})
        app.review.load_data.assert_not_called()
        GPLXApp._on_single_file_processed(app, new_item, {"rename_only": True})
        app.review.load_data.assert_called_once_with({"rename_only": True})

    def test_save_failure_keeps_current_pdf_then_success_advances_in_queue(self):
        current = {"path": "b.pdf", "filename": "b.pdf"}
        items = [{"path": "a.pdf", "status": "PENDING"}, current, {"path": "c.pdf", "status": "PENDING"}]
        app = SimpleNamespace(
            active_item=current, review=Mock(), on_file_selected=Mock(),
            sidebar=SimpleNamespace(get_item=lambda path: current, update_entry=Mock(), queue_items=items),
        )
        app._is_active = lambda item: GPLXApp._is_active(app, item)
        app._select_next_item = lambda after: GPLXApp._select_next_item(app, after=after)
        with patch("src.gui.app.messagebox.showerror") as error:
            GPLXApp._finish_folder_save(app, current, None, "Workbook locked")
        app.sidebar.update_entry.assert_called_once_with(current, "READY")
        app.on_file_selected.assert_not_called()
        error.assert_called_once()
        GPLXApp._finish_folder_save(app, current, {"pdf_path": "saved.pdf"})
        app.on_file_selected.assert_called_once_with("c.pdf")

    def test_review_name_recomputes_when_date_or_code_changes(self):
        fields = dict(province_code="15", exam_date="15/09/2015", decision_number="368",
                      decision_date="25/09/2015", suggested_province_code="")
        panel = SimpleNamespace(
            current_data={"rename_only": True, "cover_meta": {}}, _saving=False, _naming_inputs=lambda: fields,
            chk_province=Mock(), cmb_group=Mock(), _needs_table_choice=Mock(return_value=False),
            txt_proposed_filename=Mock(), group_fields={}, lbl_naming=Mock(), btn_metadata_page=Mock(), btn_confirm=Mock(),
        )
        ReviewPanel._refresh_naming(panel)
        panel.txt_proposed_filename.insert.assert_called_with(0, "15.368.25.09.2015")
        fields.update(province_code="79", decision_date="26/09/2015")
        ReviewPanel._refresh_naming(panel)
        panel.txt_proposed_filename.insert.assert_called_with(0, "79.368.26.09.2015")


if __name__ == "__main__":
    unittest.main()
