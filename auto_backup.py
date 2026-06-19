"""
auto_backup.py - V17 periodic autosave to a recoverable location.

The manager runs a QTimer that, every N minutes, packs the current canvas
of the supplied window to:

    %TEMP%/figbox_autosave/<canvas_name>__<HHMMSS>.figbox.bak

On startup, offer_recovery_if_any() scans the autosave directory and asks
the user whether to recover the most recent unfinished session.
"""

import os
import glob
import logging
from datetime import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox

import project_io as pio

logger = logging.getLogger(__name__)

BACKUP_SUFFIX = ".figbox.bak"
KEEP_LAST_N = 10


def _safe_name(name):
    """Sanitise canvas_name for use in a filename."""
    out = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "canvas"


class AutoBackupManager:
    """Background periodic backup of the active canvas as a .figbox.bak."""

    def __init__(self, window, interval_minutes=5):
        self.window = window
        self.interval_ms = max(1, int(interval_minutes)) * 60 * 1000
        self.timer = QTimer(window)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        self.timer.start()
        logger.info("AutoBackupManager started, interval=%d ms", self.interval_ms)

    def stop(self):
        self.timer.stop()
        logger.info("AutoBackupManager stopped")

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------
    def _tick(self):
        try:
            if not getattr(self.window, "current_canvas", None):
                return
            if not self.window.rect_items:
                return
            self.run_backup()
        except Exception:
            logger.exception("Autosave tick failed")

    def run_backup(self):
        """Pack current canvas to a .figbox.bak file. No-op if empty."""
        canvas = self.window.current_canvas
        if not canvas:
            return None
        try:
            project_data = self.window._build_project_data()
        except Exception as e:
            logger.warning("Skip autosave: %s", e)
            return None

        name = _safe_name(canvas.canvas_name)
        ts = datetime.now().strftime("%H%M%S")
        date = datetime.now().strftime("%Y%m%d")
        autosave_dir = pio.get_autosave_dir()
        path = os.path.join(autosave_dir, f"{name}__{date}_{ts}{BACKUP_SUFFIX}")

        asset_paths = [l.get("pdf_path") for l in project_data.get("layouts", [])
                       if l.get("pdf_path") and os.path.exists(l["pdf_path"])]
        try:
            pio.pack_figbox(path, project_data, asset_paths)
        except Exception:
            logger.exception("Autosave pack_figbox failed: %s", path)
            return None

        logger.info("Autosaved to %s", path)
        self._prune_old_backups(autosave_dir, name)
        return path

    def _prune_old_backups(self, autosave_dir, name):
        """Keep at most KEEP_LAST_N backups per canvas name."""
        pattern = os.path.join(autosave_dir, f"{name}__*{BACKUP_SUFFIX}")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for stale in files[KEEP_LAST_N:]:
            try:
                os.remove(stale)
                logger.info("Pruned old autosave %s", stale)
            except OSError as e:
                logger.warning("Could not prune %s: %s", stale, e)

    # ------------------------------------------------------------------
    # Recovery on startup
    # ------------------------------------------------------------------
    def list_backups(self):
        """Return all .figbox.bak files newest first."""
        autosave_dir = pio.get_autosave_dir()
        pattern = os.path.join(autosave_dir, f"*{BACKUP_SUFFIX}")
        return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    def offer_recovery_if_any(self):
        """Show a dialog if backups exist; load the newest if user accepts."""
        backups = self.list_backups()
        if not backups:
            return
        latest = backups[0]
        ts = datetime.fromtimestamp(os.path.getmtime(latest))
        reply = QMessageBox.question(
            self.window,
            "恢复未保存的工作",
            f"检测到 {len(backups)} 份自动备份。\n\n"
            f"最近一份: {os.path.basename(latest)}\n"
            f"时间: {ts:%Y-%m-%d %H:%M:%S}\n\n"
            f"是否打开最近的备份？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.window.load_project_from_path(latest)
            except Exception:
                logger.exception("Recovery load failed: %s", latest)
