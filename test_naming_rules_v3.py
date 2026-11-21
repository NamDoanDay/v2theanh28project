import unittest

from src.cover_parser import parse_cover_page_text
from src.naming_rules import is_valid_windows_filename_stem, propose_dossier_filename


class NamingRulesV3Test(unittest.TestCase):
    def test_examples_and_date_boundaries(self):
        cases = [
            ("79", "12/06/2008", "", "SQL", "79.SQL.06.2008.AM570000-AM570200"),
            ("79", "31/12/2012", "", "SQL", "79.SQL.12.2012.AM570000-AM570200"),
            ("15", "01/01/2013", "05/01/2013", "QĐTT", "15.368.05.01.2013"),
            ("15", "15/09/2015", "25/09/2015", "QĐTT", "15.368.25.09.2015"),
            ("15", "28/02/2025", "03/03/2025", "QĐTT", "15.368.03.03.2025"),
            ("15", "01/03/2025", "08/03/2025", "QĐSH", "15.3081.01.03.2025"),
            ("15", "01/01/2026", "", "QĐSH", "15.3081.01.01.2026"),
        ]
        for code, exam, signed, group, expected in cases:
            with self.subTest(exam=exam, signed=signed):
                proposal = propose_dossier_filename(
                    province_code=code, exam_date=exam, decision_date=signed,
                    decision_number="3081" if group == "QĐSH" else "368/QĐ-SGTVT",
                    first_license_no="AM 570000", last_license_no="am570200",
                )
                self.assertEqual((proposal.group, proposal.filename, proposal.errors), (group, expected, {}))

    def test_invalid_dates_and_confirmation_without_exam_date(self):
        fields = dict(province_code="15", decision_number="00368/QĐ-SGTVT", decision_date="29/02/2024")
        self.assertIn("exam_date", propose_dossier_filename(**fields).errors)
        for group in ("SQL", "QĐSH"):
            self.assertIn("exam_date", propose_dossier_filename(**fields, confirmed_group=group).errors)
        proposal = propose_dossier_filename(**fields, confirmed_group="QĐTT")
        self.assertEqual(proposal.filename, "15.00368.29.02.2024")
        proposal = propose_dossier_filename(**fields, confirmed_group="QĐTT", exam_date="29/02/2025")
        self.assertIn("exam_date", proposal.errors)
        self.assertIsNone(proposal.filename)
        fields["decision_date"] = "31/09/2015"
        self.assertIn("decision_date", propose_dossier_filename(**fields, confirmed_group="QĐTT").errors)

    def test_province_requires_a_selection_and_confirmation_for_conflicts(self):
        fields = dict(exam_date="01/03/2025", decision_number="3081", suggested_province_code="08")
        for code in ("", "99", "15"):
            self.assertIn("province_code", propose_dossier_filename(**fields, province_code=code).errors)
        proposal = propose_dossier_filename(**fields, province_code="15", province_confirmed=True)
        self.assertEqual(proposal.filename, "15.3081.01.03.2025")

    def test_sql_fallback_requires_a_known_empty_column(self):
        fields = dict(province_code="15", exam_date="01/05/2008")
        self.assertIsNone(propose_dossier_filename(**fields).filename)
        proposal = propose_dossier_filename(**fields, license_column_empty=True)
        self.assertEqual(proposal.filename, "15.SQL.05.2008.A000000-A000000")
        proposal = propose_dossier_filename(**fields, first_license_no="AP014542", license_column_empty=True)
        self.assertIn("last_license_no", proposal.errors)
        self.assertIsNone(proposal.filename)

    def test_decision_number_and_manual_windows_filename_validation(self):
        proposal = propose_dossier_filename(province_code="15", exam_date="01/03/2025", decision_number="abc3081")
        self.assertIn("decision_number", proposal.errors)
        for bad_name in ("", "../file", "..\\file", "AUX.1", "file.pdf", "file."):
            self.assertFalse(is_valid_windows_filename_stem(bad_name))
        self.assertTrue(is_valid_windows_filename_stem("15.3081.01.03.2025"))

    def test_cover_requires_an_explicit_exam_date(self):
        cover = parse_cover_page_text("Căn cứ văn bản ngày 22/09/2009")
        self.assertEqual((cover["exam_date"], cover["province_code"]), ("", ""))
        cover = parse_cover_page_text("Yên Bái NGÀY THI: 29 - 03 - 1996")
        self.assertEqual((cover["exam_date"], cover["province_code"]), ("29-03-1996", "15"))


if __name__ == "__main__":
    unittest.main()
