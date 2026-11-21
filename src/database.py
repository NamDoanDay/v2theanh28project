"""
Zero-Config Embedded Database Module for GPLX Management.
Uses SQLite 3 with FTS5 Full-Text Search.
No external database server or connection string required.
"""
import os
import sqlite3
import shutil
import unicodedata
import re
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import openpyxl

from src.config import DATABASE_PATH, BUNDLED_DATABASE_SEED_PATH

def remove_vietnamese_accents(text: str) -> str:
    """
    Normalizes and removes accents from Vietnamese text.
    E.g. 'Trần Văn Yên' -> 'tran van yen'
         'Đỗ Vi Thượng' -> 'do vi thuong'
    """
    if not text:
        return ""
    # Replace special characters đ/Đ
    s = text.replace("đ", "d").replace("Đ", "d")
    # Decompose unicode characters into base char + combining mark
    nfkd_form = unicodedata.normalize('NFKD', s)
    # Filter out combining marks
    res = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return res.lower().strip()

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        # Migrate the database shipped by older builds once. The live database
        # then remains in LocalAppData and survives package upgrades/re-extracts.
        if (
            db_path == DATABASE_PATH
            and BUNDLED_DATABASE_SEED_PATH
            and not os.path.exists(db_path)
            and os.path.isfile(BUNDLED_DATABASE_SEED_PATH)
        ):
            shutil.copy2(BUNDLED_DATABASE_SEED_PATH, db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Initializes tables and FTS5 full-text search index."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Dossiers Table (Sổ quản lý)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                final_filename TEXT NOT NULL UNIQUE,
                pdf_path TEXT NOT NULL,
                excel_path TEXT NOT NULL,
                province_code TEXT NOT NULL,
                book_type TEXT,
                exam_date TEXT,
                license_class TEXT,
                course TEXT,
                box TEXT,
                box_number TEXT,
                total_citizens INTEGER DEFAULT 0,
                total_pages INTEGER DEFAULT 1,
                license_sequence TEXT,
                status_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Citizens Table (Danh sách công dân)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id INTEGER NOT NULL,
                stt INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                full_name_unaccented TEXT NOT NULL,
                birth_year TEXT,
                nationality TEXT DEFAULT 'Việt Nam',
                address TEXT,
                license_number TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                FOREIGN KEY(dossier_id) REFERENCES dossiers(id) ON DELETE CASCADE
            )
            """)

            # 3. Fast Indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citizens_license ON citizens(license_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citizens_name_unaccented ON citizens(full_name_unaccented)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_citizens_birth_year ON citizens(birth_year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_filename ON dossiers(final_filename)")

            # 4. FTS5 Virtual Table for Instant Search
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS citizens_fts USING fts5(
                full_name,
                full_name_unaccented,
                license_number,
                address,
                content='citizens',
                content_rowid='id'
            )
            """)

            conn.commit()

    def insert_or_update_dossier(
        self,
        final_filename: str,
        cover_meta: Dict[str, Any],
        citizens: List[Dict[str, Any]],
        pdf_path: str,
        excel_path: str
    ) -> int:
        """
        Inserts or updates a dossier and its citizen records into SQLite.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Delete existing dossier if any
            cursor.execute("SELECT id FROM dossiers WHERE final_filename = ?", (final_filename,))
            row = cursor.fetchone()
            if row:
                dossier_id = row["id"]
                # Delete old FTS entries
                cursor.execute("DELETE FROM citizens_fts WHERE rowid IN (SELECT id FROM citizens WHERE dossier_id = ?)", (dossier_id,))
                cursor.execute("DELETE FROM citizens WHERE dossier_id = ?", (dossier_id,))
                cursor.execute("DELETE FROM dossiers WHERE id = ?", (dossier_id,))

            # Insert dossier
            cursor.execute("""
            INSERT INTO dossiers (
                final_filename, pdf_path, excel_path, province_code,
                book_type, exam_date, license_class, course,
                box, box_number, total_citizens, total_pages,
                license_sequence, status_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                final_filename,
                pdf_path,
                excel_path,
                cover_meta.get("province_code", "15"),
                cover_meta.get("book_type", "Sổ gốc cấp bằng lái xe cơ giới đường bộ"),
                cover_meta.get("exam_date", ""),
                cover_meta.get("license_class", "A1"),
                cover_meta.get("course", "25"),
                cover_meta.get("box", "48"),
                cover_meta.get("box_number", "115"),
                len(citizens),
                cover_meta.get("total_pages", 1),
                cover_meta.get("license_sequence", ""),
                cover_meta.get("status_note", "Đủ")
            ))
            dossier_id = cursor.lastrowid

            # Insert citizens
            for c in citizens:
                fn = c.get("full_name", "").strip()
                fn_unacc = remove_vietnamese_accents(fn)
                lic_no = c.get("license_number", "").strip().upper()
                stt_val = c.get("stt", 1)
                by_val = str(c.get("birth_year", "")).strip()
                nat_val = c.get("nationality", "Việt Nam").strip()
                addr_val = c.get("address", "").strip()
                p_num = c.get("page_number", 1)

                cursor.execute("""
                INSERT INTO citizens (
                    dossier_id, stt, full_name, full_name_unaccented,
                    birth_year, nationality, address, license_number, page_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (dossier_id, stt_val, fn, fn_unacc, by_val, nat_val, addr_val, lic_no, p_num))
                
                citizen_row_id = cursor.lastrowid

                # Index in FTS5
                cursor.execute("""
                INSERT INTO citizens_fts (rowid, full_name, full_name_unaccented, license_number, address)
                VALUES (?, ?, ?, ?, ?)
                """, (citizen_row_id, fn, fn_unacc, lic_no, addr_val))

            conn.commit()
            return dossier_id

    def search(
        self,
        query: str,
        province_code: Optional[str] = None,
        dossier_id: Optional[int] = None,
        limit: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Fast multi-criteria search by:
        - License Number (exact or partial, e.g. 'A461544', 'C244138')
        - Citizen Name (accented 'Trần Văn Yên' or unaccented 'tran van yen')
        - Birth Year (e.g. '1960')
        - Location
        - Dossier ID (to view all citizens within a specific imported book)
        """
        q = (query or "").strip()
        q_unaccent = remove_vietnamese_accents(q)
        q_lic = q.replace(" ", "").upper()

        if not q and not dossier_id:
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            sql = """
            SELECT 
                c.id as citizen_id,
                c.stt,
                c.full_name,
                c.birth_year,
                c.nationality,
                c.address,
                c.license_number,
                c.page_number,
                d.id as dossier_id,
                d.final_filename,
                d.pdf_path,
                d.excel_path,
                d.province_code,
                d.box,
                d.box_number,
                d.license_class,
                d.course,
                d.exam_date
            FROM citizens c
            JOIN dossiers d ON c.dossier_id = d.id
            WHERE 1=1
            """
            params = []

            if q:
                sql += """
                AND (
                    c.license_number LIKE ?
                    OR c.full_name_unaccented LIKE ?
                    OR c.full_name LIKE ?
                    OR c.birth_year = ?
                )
                """
                params.extend([
                    f"%{q_lic}%",
                    f"%{q_unaccent}%",
                    f"%{q}%",
                    q
                ])

            if province_code and province_code != "all":
                sql += " AND d.province_code = ?"
                params.append(province_code)

            if dossier_id:
                sql += " AND d.id = ?"
                params.append(dossier_id)

            sql += " ORDER BY c.id ASC"
            if not dossier_id:
                sql += " LIMIT ?"
                params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_all_dossiers(
        self,
        province_code: Optional[str] = "all",
        box: Optional[str] = "all",
        search_kw: str = "",
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all imported dossiers/Excel registers with box, box_number and license statistics.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            SELECT 
                d.id,
                d.final_filename,
                d.pdf_path,
                d.excel_path,
                d.province_code,
                d.book_type,
                d.exam_date,
                d.license_class,
                d.course,
                d.box,
                d.box_number,
                d.total_citizens,
                d.total_pages,
                d.license_sequence,
                d.status_note,
                d.created_at
            FROM dossiers d
            WHERE 1=1
            """
            params = []
            if province_code and province_code != "all":
                sql += " AND d.province_code = ?"
                params.append(province_code)
            if box and box != "all":
                sql += " AND d.box = ?"
                params.append(box)
            if search_kw and search_kw.strip():
                sql += " AND (d.final_filename LIKE ? OR d.box LIKE ? OR d.box_number LIKE ?)"
                kw = f"%{search_kw.strip()}%"
                params.extend([kw, kw, kw])
            
            sql += " ORDER BY d.id DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_inventory_stats(self) -> Dict[str, Any]:
        """
        Calculates aggregate inventory statistics across all imported files and boxes.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT province_code) FROM dossiers")
            total_provinces = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT box) FROM dossiers WHERE box IS NOT NULL AND box != ''")
            total_boxes = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT box || '_' || box_number) FROM dossiers WHERE box_number IS NOT NULL AND box_number != ''")
            total_box_numbers = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM dossiers")
            total_dossiers = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM citizens")
            total_citizens = cursor.fetchone()[0] or 0

            return {
                "total_provinces": total_provinces,
                "total_boxes": total_boxes,
                "total_box_numbers": total_box_numbers,
                "total_dossiers": total_dossiers,
                "total_citizens": total_citizens
            }

    def get_distinct_boxes(self, province_code: str = "all") -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if province_code and province_code != "all":
                cursor.execute("SELECT DISTINCT box FROM dossiers WHERE province_code = ? AND box IS NOT NULL AND box != '' ORDER BY box ASC", (province_code,))
            else:
                cursor.execute("SELECT DISTINCT box FROM dossiers WHERE box IS NOT NULL AND box != '' ORDER BY box ASC")
            return [str(r[0]) for r in cursor.fetchall()]

    def get_stats(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dossiers")
            total_dossiers = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM citizens")
            total_citizens = cursor.fetchone()[0]
            return {
                "total_dossiers": total_dossiers,
                "total_citizens": total_citizens
            }

    def reindex_from_directory(self, root_dir: str) -> int:
        """
        Scans a directory for companion .xlsx files and re-indexes them into SQLite.
        """
        indexed_count = 0
        for root, _, files in os.walk(root_dir):
            for f in files:
                if f.endswith(".xlsx") and not f.startswith("So_Theo_Doi_"):
                    excel_path = os.path.join(root, f)
                    base_name = f[:-5]
                    pdf_path = os.path.join(root, f"{base_name}.pdf")
                    if os.path.exists(pdf_path):
                        try:
                            self._index_single_excel(excel_path, pdf_path, base_name)
                            indexed_count += 1
                        except Exception as e:
                            print(f"Error reindexing {excel_path}: {e}")
        return indexed_count

    def _index_single_excel(self, excel_path: str, pdf_path: str, final_filename: str):
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active
        
        # Parse metadata from top rows
        title_meta = str(ws["A2"].value or "")
        date_meta = str(ws["A3"].value or "")
        
        # Extract province code
        prov_match = re.search(r"Mã tỉnh:\s*([0-9]+)", title_meta)
        prov_code = prov_match.group(1) if prov_match else "15"

        hang_match = re.search(r"Hạng:\s*([A-Za-z0-9]+)", title_meta)
        hang = hang_match.group(1) if hang_match else "A1"

        khoa_match = re.search(r"Khóa:\s*([A-Za-z0-9]+)", title_meta)
        khoa = khoa_match.group(1) if khoa_match else ""

        date_match = re.search(r"Ngày thi:\s*([0-9\-/.]+)", date_meta)
        exam_date = date_match.group(1) if date_match else ""

        citizens = []
        for r in range(6, ws.max_row + 1):
            stt_val = ws.cell(row=r, column=1).value
            name_val = ws.cell(row=r, column=2).value
            if not name_val:
                continue
            citizens.append({
                "stt": stt_val or (r - 5),
                "full_name": str(name_val).strip(),
                "birth_year": str(ws.cell(row=r, column=3).value or "").strip(),
                "nationality": str(ws.cell(row=r, column=4).value or "Việt Nam").strip(),
                "address": str(ws.cell(row=r, column=5).value or "").strip(),
                "license_number": str(ws.cell(row=r, column=6).value or "").strip(),
                "page_number": int(ws.cell(row=r, column=7).value or 1)
            })

        cover_meta = {
            "province_code": prov_code,
            "book_type": "Sổ gốc cấp bằng lái xe cơ giới đường bộ",
            "license_class": hang,
            "course": khoa,
            "exam_date": exam_date,
            "box": "48",
            "box_number": "115",
            "total_pages": max([c["page_number"] for c in citizens]) if citizens else 1,
            "license_sequence": "",
            "status_note": "Đủ"
        }

        self.insert_or_update_dossier(
            final_filename=final_filename,
            cover_meta=cover_meta,
            citizens=citizens,
            pdf_path=pdf_path,
            excel_path=excel_path
        )
