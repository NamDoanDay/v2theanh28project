import faulthandler
import os
import sys
import threading
import tempfile
import unittest
import sqlite3

from src import logger as app_logger
from src.database import DatabaseManager


class LoggingTests(unittest.TestCase):
    def test_rotating_file_records_diagnostics_and_traceback(self):
        old_excepthook = sys.excepthook
        old_thread_hook = getattr(threading, "excepthook", None)
        old_unraisable_hook = getattr(sys, "unraisablehook", None)
        with tempfile.TemporaryDirectory() as log_dir:
            try:
                logger = app_logger.configure_logging(log_dir)
                try:
                    raise ValueError("diagnostic test")
                except ValueError:
                    logger.exception("Expected test exception")

                log_path = os.path.join(log_dir, "app_%s.log" % app_logger.date.today().isoformat())
                with open(log_path, encoding="utf-8") as log_file:
                    contents = log_file.read()
                self.assertIn("INFO", contents)
                self.assertIn("pid=", contents)
                self.assertIn("tid=", contents)
                self.assertIn("ValueError: diagnostic test", contents)
                self.assertTrue(os.path.exists(os.path.join(log_dir, "native_crash.log")))
                self.assertIs(sys.excepthook, app_logger._handle_uncaught)
            finally:
                sys.excepthook = old_excepthook
                if old_thread_hook is not None:
                    threading.excepthook = old_thread_hook
                if old_unraisable_hook is not None:
                    sys.unraisablehook = old_unraisable_hook
                faulthandler.disable()
                if app_logger._crash_file:
                    app_logger._crash_file.close()
                    app_logger._crash_file = None
                for handler in app_logger.get_logger().handlers[:]:
                    handler.close()
                    app_logger.get_logger().removeHandler(handler)

    def test_database_connection_context_closes_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = DatabaseManager(os.path.join(temp_dir, "test.db"))
            with db.get_connection() as connection:
                connection.execute("SELECT 1")
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
