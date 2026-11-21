"""Application logging and uncaught-exception diagnostics."""
import faulthandler
import logging
import os
import platform
import sys
import tempfile
import threading
from datetime import date
from logging.handlers import RotatingFileHandler


APP_VERSION = "2.0"
_logger = logging.getLogger("gplx")
_crash_file = None
_exception_notifier = None


def _stderr_fallback(message):
    try:
        if sys.__stderr__:
            sys.__stderr__.write(message + "\n")
    except Exception:
        return


def _log_directory():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return os.path.join(base, "GPLX", "logs")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/GPLX")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
        return os.path.join(base, "gplx", "logs")
    return os.path.join(tempfile.gettempdir(), "GPLX", "logs")


def _handle_uncaught(exc_type, exc_value, exc_traceback):
    try:
        _logger.critical(
            "Uncaught exception on main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
    except Exception as logging_error:
        _stderr_fallback("Could not record uncaught exception: %s" % logging_error)
    title = "Lỗi ứng dụng"
    message = "%s: %s" % (exc_type.__name__, exc_value)
    if _exception_notifier:
        _notify_exception(title, message)
    else:
        try:
            from tkinter import messagebox
            messagebox.showerror(title, message + "\n\nChi tiết đã được ghi vào file log.")
        except Exception as popup_error:
            _stderr_fallback("Could not display fatal error popup: %s" % popup_error)


def _handle_thread_exception(args):
    try:
        _logger.critical(
            "Uncaught exception in thread %s", args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    except Exception as logging_error:
        _stderr_fallback("Could not record background-thread exception: %s" % logging_error)
    _notify_exception(
        "Lỗi tác vụ nền",
        "Luồng %s gặp lỗi: %s: %s" % (
            args.thread.name if args.thread else "unknown", args.exc_type.__name__, args.exc_value,
        ),
    )


def _handle_unraisable(args):
    try:
        _logger.error(
            "Unraisable exception in %r", args.object,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
    except Exception as logging_error:
        _stderr_fallback("Could not record unraisable exception: %s" % logging_error)
    _notify_exception("Lỗi ứng dụng", "%s: %s" % (args.exc_type.__name__, args.exc_value))


def _notify_exception(title, message):
    if _exception_notifier:
        try:
            _exception_notifier(title, message)
        except Exception as notifier_error:
            _stderr_fallback("Could not show exception notification: %s" % notifier_error)


def set_exception_notifier(callback):
    """Register an optional UI-safe callback for global exception popups."""
    global _exception_notifier
    _exception_notifier = callback


def configure_logging(log_dir=None):
    """Configure rotating file logs and process-wide exception diagnostics."""
    global _crash_file
    if _logger.handlers:
        return _logger

    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s.%(module)s.%(funcName)s:%(lineno)d] "
        "[pid=%(process)d tid=%(thread)d] %(message)s"
    )

    try:
        log_dir = log_dir or _log_directory()
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app_%s.log" % date.today().isoformat())
        file_handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
        _crash_file = open(os.path.join(log_dir, "native_crash.log"), "a", encoding="utf-8")
        faulthandler.enable(file=_crash_file, all_threads=True)
    except (OSError, RuntimeError, ValueError):
        # Keep startup available if the preferred diagnostics directory is read-only.
        try:
            fallback_dir = os.path.join(tempfile.gettempdir(), "GPLX", "logs")
            os.makedirs(fallback_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                os.path.join(fallback_dir, "app_%s.log" % date.today().isoformat()),
                maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)
        except (OSError, RuntimeError, ValueError) as fallback_error:
            _stderr_fallback("Could not create fallback log file: %s" % fallback_error)

    if not getattr(sys, "frozen", False) and sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)

    sys.excepthook = _handle_uncaught
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception
    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = _handle_unraisable

    _logger.info(
        "Application started: version=%s python=%s os=%s executable=%s cwd=%s",
        APP_VERSION, sys.version.replace("\n", " "), platform.platform(), sys.executable, os.getcwd(),
    )
    return _logger


def get_logger(name=None):
    return _logger if not name else logging.getLogger("gplx.%s" % name)
