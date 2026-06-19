"""
Canvas Widget for V9 - Encapsulates a single canvas with all its state and operations.
This allows multiple independent canvases to be managed in tabs.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGraphicsScene, QListWidget,
                             QListWidgetItem, QMessageBox, QGraphicsRectItem)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont

from pdf_utils import PDFInfo, points_to_mm, get_effective_pdf_path
from layout_engine import LayoutItem
import fitz
import os


class CanvasWidget(QWidget):
    """A widget containing a single canvas with its own state."""

    def __init__(self, parent_gui, canvas_name="未命名画布", canvas_width=297, canvas_height=210):
        """
        Initialize a canvas widget.

        Args:
            parent_gui: Reference to the main FigureCombinerGUI window
            canvas_name: Name of this canvas (for tab label)
            canvas_width: Canvas width in mm
            canvas_height: Canvas height in mm
        """
        super().__init__()

        # Reference to parent
        self.parent_gui = parent_gui

        # Canvas properties
        self.canvas_name = canvas_name
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Canvas-specific state
        self.pdf_files = []
        self.current_layouts = []
        self.rect_items = []
        self.folder_path = ""

        # Import HistoryManager from parent module (V17: renamed from gui_editor_v9)
        from gui_editor import HistoryManager
        self.history = HistoryManager()
        self.history_blocked = False

        # Grid and guides settings
        self.grid_size = 5.0  # mm
        self.snap_enabled = False
        self.show_guides = False
        self.show_ruler = False
        self.guide_lines = []

        # Scene and view are managed by parent, not widget
        # We just store references
        self.scene = None
        self.view = None
        self.file_list = None

    def get_canvas_width(self):
        """Get canvas width in mm."""
        return self.canvas_width

    def get_canvas_height(self):
        """Get canvas height in mm."""
        return self.canvas_height

    def set_canvas_size(self, width, height):
        """Set canvas size and update display."""
        self.canvas_width = width
        self.canvas_height = height
        if self.scene:
            self.update_canvas_rectangle()

    def update_canvas_rectangle(self):
        """Update canvas rectangle size."""
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, 'is_canvas_rect'):
                item.setRect(0, 0, self.canvas_width, self.canvas_height)
                return

    def get_display_name(self):
        """Get display name for tab."""
        pdf_count = len(self.pdf_files)
        if pdf_count > 0:
            return f"{self.canvas_name} ({pdf_count})"
        return self.canvas_name

    def snapshot_state(self):
        """Capture current layout snapshot for history."""
        if not self.rect_items:
            return []
        return [item.get_current_state() for item in self.rect_items]

    def capture_history_state(self, status_message=None):
        """Capture a snapshot into history."""
        if self.history_blocked:
            return
        snapshot = self.snapshot_state()
        self.history.capture(snapshot)
        if status_message and self.parent_gui:
            self.parent_gui.statusBar().showMessage(f"{status_message} | Ctrl+Z可撤销")

    def has_unsaved_changes(self):
        """Check if there are unsaved changes."""
        # Simple check: if there are any PDF files or layouts
        return len(self.pdf_files) > 0 or len(self.current_layouts) > 0

    def clear_canvas(self):
        """Clear all content from this canvas - V15 FIX."""
        # V15 FIX: Use clear() to maintain list reference consistency
        self.pdf_files.clear()
        self.current_layouts.clear()
        self.rect_items.clear()
        self.folder_path = ""
        if self.scene:
            self.scene.clear()
        if self.file_list:
            self.file_list.clear()
        self.history.reset([])
