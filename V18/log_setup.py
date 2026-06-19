"""
log_setup.py - V17 centralised logging.

Writes rotating logs under %USERPROFILE%/.figbox/logs/figbox_<YYYYMMDD>.log
plus a stderr handler for development. Safe to call multiple times.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


_LOG_DIR_NAME = ".figbox"
_INITIALISED = False


def get_log_dir():
    """Return (and create) the directory where log files live."""
    home = os.path.expanduser("~")
    log_dir = os.path.join(home, _LOG_DIR_NAME, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging(level=logging.INFO):
    """Configure root logger. Returns the path of the active log file.

    Idempotent: if called twice, the second call returns the existing path
    without adding duplicate handlers.
    """
    global _INITIALISED
    log_dir = get_log_dir()
    log_path = os.path.join(log_dir, f"figbox_{datetime.now():%Y%m%d}.log")

    if _INITIALISED:
        return log_path

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    # Rotating file handler: keep 5 files of up to 2 MB each
    fh = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024,
                             backupCount=5, encoding="utf-8")
    fh.setFormatter(formatter)
    fh.setLevel(level)
    root.addHandler(fh)

    # Mirror to stderr so that dev runs still see logs in the console
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(formatter)
    sh.setLevel(level)
    root.addHandler(sh)

    _INITIALISED = True
    logging.getLogger("log_setup").info("Logging initialised -> %s", log_path)
    return log_path
