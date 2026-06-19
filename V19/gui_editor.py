"""PyQt5 GUI for interactive figure layout editor - Version 19.

V19 New Features (Proportional Fill Edition):
1. 删除 7 个低效自动排版（规则网格/紧凑/黄金分割/瀑布流/智能分组/自适应权重/AI智能布局）
2. 📐 填充剩余宽度：选中图乘以同一系数（保留各自比例与相对大小），自动识别本行
   右侧剩余画布宽度并顺序填满，与本行已有图顶部对齐（不强行等高）
3. 标签级联联动：改标签为已存在标签时其余自动顺延，始终保持 A、B、C… 连续
4. 导出默认 1000 DPI（出版级）；屏幕预览仍用低 DPI，保证流畅
5. 导入后用"全局统一缩放换行"做初始铺排，供后续精修
6. 完全兼容 V18 的 .figbox / .figproj 项目文件
   （一键自动排版暂缓，待"填充剩余宽度"用顺后再设计）

V17 New Features (FigBox Container Edition):
1. Self-contained .figbox project container (ZIP packaging assets + layout)
2. Project file no longer breaks when source images are moved/renamed/deleted
3. Double-click .figbox to open after running register_figbox.bat
4. One-click upgrade of legacy .figproj into .figbox
5. Five-minute autosave to a recoverable backup
6. Centralised logging under %USERPROFILE%/.figbox/logs/

V16 Features (Enhanced Export Edition - Inherited):
1. 📋 智能粘贴 + 画布间复制 - Ctrl+C/V支持跨画布复制粘贴，智能识别系统/内部剪贴板
2. 🎯 1000DPI导出选项 - 新增超高分辨率导出支持
3. 📝 导出图片信息记录 - 自动生成Markdown文件记录图片来源
4. ⚠️ 文件覆盖确认 - 导出前智能检测同名文件并确认
5. 🔒 关闭软件确认 - 退出时弹出确认对话框防止误操作

V15 Features (Canvas Sync Stability - Inherited):
1. 🔧 彻底修复多画布状态同步问题
2. 📦 修复代理变量引用断开问题
3. 🔄 添加 _sync_to_canvas() 同步机制
4. 🖼️ 修复导出图片被截断问题
5. 🔃 修复旋转图片导出位置偏移

V9 Features (Multi-Canvas Management - Inherited):
1. 多画布管理 - 同时打开多个画布进行不同的组图项目
2. 标签页切换 - 可以在不同画布之间快速切换
3. 独立画布设置 - 每个画布有独立的参数和布局
4. 新增/关闭画布 - 灵活管理多个组图项目

V8 Features (Inherited):
1. 修复拖拽图片时的蓝色重影问题
2. 支持拖拽PDF文件导入
3. 键盘方向键移动图片
4. 图片旋转功能（90°/180°/270°）
5. 批量缩放到相同大小（宽度/高度）
6. 智能对齐辅助线
7. 网格吸附功能
8. 标尺和参考线显示
9. 图片间距批量调整
10. 启动即显示空白画布
"""

import sys
import os
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QListWidget, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsTextItem, QComboBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QSplitter,
                             QGroupBox, QFormLayout, QMessageBox, QListWidgetItem,
                             QGraphicsItem, QGraphicsPixmapItem, QDockWidget,
                             QProgressDialog, QToolBar, QAction, QMenu, QGraphicsLineItem,
                             QInputDialog, QTabWidget, QTabBar)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QThread, QLineF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont, QPixmap, QImage, QTransform, QKeySequence, QCursor

from pdf_utils import scan_pdf_folder, PDFInfo, CANVAS_PRESETS, mm_to_points, points_to_mm, get_pdf_page_as_pixmap
from layout_engine import LayoutEngine, LayoutItem
from canvas_widget import CanvasWidget
from themes import DarkTheme, LightTheme, CuteTheme, apply_theme, get_theme_names  # V12: Import theme system
import fitz

import project_io as pio  # V17: figbox container I/O
import logging
from settings_manager import load_user_settings, save_settings
logger = logging.getLogger(__name__)


class HistoryManager:
    """Simple snapshot-based history for undo/redo."""

    def __init__(self, limit=200):
        self.limit = limit
        self.states = []
        self.index = -1

    def reset(self, snapshot):
        """Reset history with initial snapshot."""
        self.states = [snapshot]
        self.index = 0

    def capture(self, snapshot):
        """Capture a new snapshot and truncate redo branch."""
        if self.index < len(self.states) - 1:
            self.states = self.states[:self.index + 1]

        self.states.append(snapshot)
        if len(self.states) > self.limit:
            self.states.pop(0)
        self.index = len(self.states) - 1

    def can_undo(self):
        return self.index > 0

    def can_redo(self):
        return self.index < len(self.states) - 1

    def undo_state(self):
        if not self.can_undo():
            return None
        self.index -= 1
        return self.states[self.index]

    def redo_state(self):
        if not self.can_redo():
            return None
        self.index += 1
        return self.states[self.index]


class CanvasView(QGraphicsView):
    """Custom graphics view with keyboard+mouse navigation and drag-drop support - V11 Enhanced."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        # Disable all default drag modes
        self.setDragMode(QGraphicsView.NoDrag)

        # Track mouse state
        self.setMouseTracking(True)

        # V11: Use default arrow cursor (no more hand cursor)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)

        # V11: Enable wheel events and set focus policy
        self.setFocusPolicy(Qt.StrongFocus)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # V11 NEW: Right-button drag for panning
        self.is_panning = False
        self.pan_start_pos = None

        # V8: Enable drag and drop for PDF files
        self.setAcceptDrops(True)

        # V8: Reference to main window (will be set later)
        self.main_window = None

        # V8: Alignment guide lines
        self.alignment_lines = []
        self.show_alignment_guides = True

        # V19: 画线模式（用于"等高填充"指定宽度）
        self.fill_line_mode = False
        self._fill_line_start = None
        self._fill_line_item = None
        self._fill_line_callback = None

    def start_fill_line(self, callback):
        """V19: 进入画线模式。用户拖出一条横线后，回调 callback(x_left, x_right, y)（场景坐标=mm）。"""
        self.fill_line_mode = True
        self._fill_line_start = None
        self._fill_line_callback = callback
        self.viewport().setCursor(Qt.CrossCursor)
        self.setCursor(Qt.CrossCursor)

    def _cancel_fill_line(self):
        """退出画线模式并清理临时线条。"""
        self.fill_line_mode = False
        self._fill_line_start = None
        self._fill_line_callback = None
        if self._fill_line_item is not None and self.scene() is not None:
            self.scene().removeItem(self._fill_line_item)
        self._fill_line_item = None
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)

    def _is_on_figure_item(self, pos):
        """Check if position is on a ResizableRectItem (actual figure), not background."""
        item = self.itemAt(pos)
        while item is not None:
            if isinstance(item, ResizableRectItem):
                return True
            item = item.parentItem()
        return False

    def mousePressEvent(self, event):
        """Handle mouse press - V11: Support rubber band selection and right-button panning."""
        # V19: 画线模式优先 —— 左键按下记录起点，开始画一条横线
        if self.fill_line_mode:
            if event.button() == Qt.LeftButton:
                from PyQt5.QtWidgets import QGraphicsLineItem
                from PyQt5.QtGui import QPen, QColor
                start = self.mapToScene(event.pos())
                self._fill_line_start = start
                line = QGraphicsLineItem(start.x(), start.y(), start.x(), start.y())
                pen = QPen(QColor(220, 30, 30))
                pen.setStyle(Qt.DashLine)
                pen.setCosmetic(True)   # 宽度不随缩放变化
                pen.setWidth(2)
                line.setPen(pen)
                line.setZValue(10000)
                self.scene().addItem(line)
                self._fill_line_item = line
                event.accept()
                return
            elif event.button() == Qt.RightButton:
                # 右键取消画线
                self._cancel_fill_line()
                if self.main_window:
                    self.main_window.statusBar().showMessage("已取消画线填充", 3000)
                event.accept()
                return

        # V11 NEW: Right button on empty space = Start panning
        if event.button() == Qt.RightButton:
            if not self._is_on_figure_item(event.pos()):
                self.is_panning = True
                self.pan_start_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return

        # V11 NEW: Left button - rubber band selection on empty space
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            # If not clicking on a figure item, enable rubber band selection
            if not self._is_on_figure_item(event.pos()):
                self.setDragMode(QGraphicsView.RubberBandDrag)
            else:
                self.setDragMode(QGraphicsView.NoDrag)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move - V11: Support right-button panning."""
        # V19: 画线模式 —— 拖动时实时更新横线（约束为水平线，y 固定为起点 y）
        if self.fill_line_mode and self._fill_line_start is not None and self._fill_line_item is not None:
            cur = self.mapToScene(event.pos())
            y = self._fill_line_start.y()
            self._fill_line_item.setLine(self._fill_line_start.x(), y, cur.x(), y)
            event.accept()
            return

        # V11 NEW: Handle right-button panning
        if self.is_panning and self.pan_start_pos is not None:
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()

            # Move the scrollbars
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        super().mouseMoveEvent(event)

        # V8 FIX: Force scene update to prevent blue ghosting
        if self.scene():
            self.scene().update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - V11: Stop panning and rubber band."""
        # V19: 画线模式 —— 松开左键即完成，回调宽度信息后退出画线模式
        if self.fill_line_mode and event.button() == Qt.LeftButton and self._fill_line_start is not None:
            end = self.mapToScene(event.pos())
            x_left = min(self._fill_line_start.x(), end.x())
            x_right = max(self._fill_line_start.x(), end.x())
            y = self._fill_line_start.y()
            callback = self._fill_line_callback
            self._cancel_fill_line()
            if callback:
                callback(x_left, x_right, y)
            event.accept()
            return

        # V11 NEW: Stop panning
        if event.button() == Qt.RightButton and self.is_panning:
            self.is_panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        # Stop rubber band selection
        if self.dragMode() == QGraphicsView.RubberBandDrag:
            self.setDragMode(QGraphicsView.NoDrag)

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """V13 ENHANCED: Universal wheel navigation.

        - Mouse wheel (anywhere): Zoom in/out
        - Ctrl + Mouse wheel: Horizontal scroll (left/right)
        """
        modifiers = QApplication.keyboardModifiers()
        delta = event.angleDelta().y()

        if delta == 0:
            event.ignore()
            return

        # Ctrl + Wheel: Horizontal scroll (regardless of position)
        if modifiers & Qt.ControlModifier:
            scroll_bar = self.horizontalScrollBar()
            scroll_amount = delta
            scroll_bar.setValue(scroll_bar.value() - scroll_amount)
            event.accept()
            return

        # V13 ENHANCED: Wheel anywhere = Zoom (removed position restriction!)
        zoom_factor = 1.15
        if delta > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events - V11."""
        # V10 NEW: Handle Ctrl+V for paste
        if event.matches(QKeySequence.Paste) or (event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V):
            if self.main_window:
                self.main_window.paste_from_clipboard()
                event.accept()
                return

        # V8修复：方向键移动功能需要转发到主窗口处理
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if self.main_window:
                self.main_window.move_selected_with_arrow_keys(event.key())
                event.accept()
                return
        # 其他按键正常处理
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Handle key release events - V11."""
        super().keyReleaseEvent(event)

    def leaveEvent(self, event):
        """Reset cursor when leaving view - V11: Always arrow cursor."""
        super().leaveEvent(event)

    def enterEvent(self, event):
        """Set cursor when entering view - V11: Always arrow cursor."""
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setCursor(Qt.ArrowCursor)
        super().enterEvent(event)

    # V10: Drag and drop support for PDF and image files
    def dragEnterEvent(self, event):
        """Handle drag enter event for PDF and image files."""
        if event.mimeData().hasUrls():
            # Check if any URL is a supported file (PDF, TIF, PNG, JPG)
            supported_exts = ('.pdf', '.tif', '.tiff', '.png', '.jpg', '.jpeg')
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(supported_exts):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event for PDF and image files - V10 Enhanced."""
        if event.mimeData().hasUrls():
            files = []
            supported_exts = ('.pdf', '.tif', '.tiff', '.png', '.jpg', '.jpeg')
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if filepath.lower().endswith(supported_exts):
                    files.append(filepath)

            if files and self.main_window:
                # V19: 把落点（场景坐标 = mm）传下去，图就落在拖放的位置
                scene_pos = self.mapToScene(event.pos())
                self.main_window.import_dropped_files(
                    files, drop_pos=(scene_pos.x(), scene_pos.y()))
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class ResizableRectItem(QGraphicsRectItem):
    """Resizable, draggable rectangle item - V8 with rotation and enhanced features."""

    def __init__(self, layout_item: LayoutItem, gui, parent=None):
        super().__init__(parent)
        self.layout_item = layout_item
        self.gui = gui
        self.handle_size = 8
        self.is_rotating = False
        self.is_resizing = False
        self.is_multi_resizing = False
        self.rotation_start_angle = 0
        self._multi_resize_items = []
        self._multi_resize_start_rects = {}

        # Track positions for undo
        self.old_pos = None
        self.old_rect = None

        # V8: Grid snapping
        self.snap_to_grid = False

        # Set up appearance
        self.setPen(QPen(QColor(0, 120, 215), 2))
        self.setBrush(QBrush(QColor(200, 230, 255, 100)))

        # Enable interactions
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        # Set initial geometry
        self.setRect(0, 0, layout_item.width, layout_item.height)
        self.setPos(layout_item.x, layout_item.y)
        self.setRotation(layout_item.rotation)

        # Add label text
        self.label_text = QGraphicsTextItem(layout_item.label, self)
        font = QFont("Arial", 12, QFont.Bold)
        self.label_text.setFont(font)
        self.label_text.setDefaultTextColor(QColor(0, 0, 0))
        self.update_label_position()

        # Store thumbnail
        self.thumbnail = None
        self.load_thumbnail()

    def load_thumbnail(self):
        """Load PDF thumbnail for preview - V11: Handle missing files."""
        try:
            from pdf_utils import get_pdf_page_as_pixmap, get_effective_pdf_path
            import os

            # V11 NEW: Check if PDF is missing
            if hasattr(self.layout_item.pdf_info, 'is_missing') and self.layout_item.pdf_info.is_missing:
                # Create placeholder thumbnail for missing PDF
                self.create_placeholder_thumbnail()
                return

            pdf_path = get_effective_pdf_path(self.layout_item.pdf_info)

            # V11 NEW: Double check file exists before loading
            if not os.path.exists(pdf_path):
                self.create_placeholder_thumbnail()
                return

            pix = get_pdf_page_as_pixmap(pdf_path, dpi=72)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.thumbnail = QPixmap.fromImage(img)
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            self.create_placeholder_thumbnail()

    def create_placeholder_thumbnail(self):
        """V12: Create a placeholder thumbnail for missing PDF files."""
        # Create a simple placeholder image
        width = int(self.layout_item.width) or 200
        height = int(self.layout_item.height) or 200

        # V12: Create QPixmap with current theme background (with fallback)
        pixmap = QPixmap(width, height)
        if hasattr(self.gui, 'current_theme_class'):
            bg_color = getattr(self.gui.current_theme_class, 'BG_MEDIUM', '#2d2d30')
            fg_color = getattr(self.gui.current_theme_class, 'FG_SECONDARY', '#999999')
        else:
            # Fallback to dark theme colors
            bg_color = '#2d2d30'
            fg_color = '#999999'

        pixmap.fill(QColor(bg_color))

        # V12: Draw warning text with theme colors
        painter = QPainter(pixmap)
        painter.setPen(QColor(fg_color))

        # Draw diagonal lines
        painter.drawLine(0, 0, width, height)
        painter.drawLine(0, height, width, 0)

        # Draw text
        font = QFont("Arial", max(12, height // 10))
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "PDF\n文件丢失")

        painter.end()
        self.thumbnail = pixmap

    def contextMenuEvent(self, event):
        """Handle right-click context menu - V8 Enhanced with rotation."""
        menu = QMenu()

        # Label editing submenu
        label_menu = menu.addMenu("✏️ 修改标签")
        for i in range(26):
            label = chr(65 + i)
            action = label_menu.addAction(label)
            action.triggered.connect(lambda checked, lbl=label: self.change_label(lbl))

        menu.addSeparator()

        # V8 NEW: Rotation submenu
        rotate_menu = menu.addMenu("🔄 旋转")

        action_rotate_90 = rotate_menu.addAction("↻ 顺时针90°")
        action_rotate_90.triggered.connect(lambda: self.rotate_item(90))

        action_rotate_180 = rotate_menu.addAction("↻ 180°")
        action_rotate_180.triggered.connect(lambda: self.rotate_item(180))

        action_rotate_270 = rotate_menu.addAction("↺ 逆时针90°")
        action_rotate_270.triggered.connect(lambda: self.rotate_item(270))

        action_rotate_reset = rotate_menu.addAction("⟲ 重置旋转")
        action_rotate_reset.triggered.connect(lambda: self.rotate_item(0, absolute=True))

        menu.addSeparator()

        # V8 NEW: 多级PDF边界扩展菜单
        expand_menu = menu.addMenu("📐 PDF边界扩展")

        # 边距选项（points）
        margins = [
            ('极小', 2),
            ('小', 10),
            ('标准', 20),
            ('中', 30),
            ('大', 50),
            ('很大', 80),
            ('最大', 100)
        ]

        # 全部方向子菜单
        all_dir_menu = expand_menu.addMenu("🔲 全部方向")
        for name, margin in margins:
            action = all_dir_menu.addAction(f"{name} ({margin}点)")
            action.triggered.connect(lambda checked, m=margin: self.expand_pdf_boundary_auto(m, True, True, True, True))

        expand_menu.addSeparator()

        # 上方向子菜单
        top_menu = expand_menu.addMenu("⬆️ 向上扩展")
        for name, margin in margins:
            action = top_menu.addAction(f"{name} ({margin}点)")
            action.triggered.connect(lambda checked, m=margin: self.expand_pdf_boundary_auto(m, False, False, True, False))

        # 下方向子菜单
        bottom_menu = expand_menu.addMenu("⬇️ 向下扩展")
        for name, margin in margins:
            action = bottom_menu.addAction(f"{name} ({margin}点)")
            action.triggered.connect(lambda checked, m=margin: self.expand_pdf_boundary_auto(m, False, False, False, True))

        # 左方向子菜单
        left_menu = expand_menu.addMenu("⬅️ 向左扩展")
        for name, margin in margins:
            action = left_menu.addAction(f"{name} ({margin}点)")
            action.triggered.connect(lambda checked, m=margin: self.expand_pdf_boundary_auto(m, True, False, False, False))

        # 右方向子菜单
        right_menu = expand_menu.addMenu("➡️ 向右扩展")
        for name, margin in margins:
            action = right_menu.addAction(f"{name} ({margin}点)")
            action.triggered.connect(lambda checked, m=margin: self.expand_pdf_boundary_auto(m, False, True, False, False))

        expand_menu.addSeparator()

        # 恢复原始边界
        if self.layout_item.pdf_info.expand_boundary:
            action_restore = expand_menu.addAction("⟲ 恢复原始边界")
            action_restore.triggered.connect(self.restore_pdf_boundary)

        menu.addSeparator()

        # Delete option
        action_delete = menu.addAction("🗑️ 删除")
        action_delete.triggered.connect(lambda: self.gui.delete_selected())

        menu.exec_(event.screenPos())
        event.accept()

    def change_label(self, new_label):
        """V19: 修改标签并级联联动——其余标签自动顺延保持 A.. 连续。"""
        self.gui.relabel_insert(self, new_label)

    def rotate_item(self, angle, absolute=False):
        """Rotate the item - V8 NEW.

        Args:
            angle: Rotation angle in degrees
            absolute: If True, set absolute rotation; if False, add to current rotation
        """
        old_rotation = self.rotation()

        if absolute:
            new_rotation = angle
        else:
            new_rotation = (old_rotation + angle) % 360

        self.setRotation(new_rotation)
        self.layout_item.rotation = new_rotation

        self.gui.capture_history_state(f"已旋转图片 {angle}°")
        self.gui.statusBar().showMessage(f"已旋转图片 {angle}°，当前角度: {new_rotation}°")

    def expand_pdf_boundary(self, margin=20):
        """扩展PDF边界以显示被裁剪的内容"""
        try:
            from pdf_boundary_fix import expand_pdf_bounds
            import tempfile
            import os

            old_temp_path = self.layout_item.pdf_info.expanded_filepath
            if old_temp_path:
                try:
                    os.remove(old_temp_path)
                except:
                    pass

            self.layout_item.pdf_info.cumulative_margin += margin

            fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)

            expanded_path = expand_pdf_bounds(
                self.layout_item.pdf_info.filepath,
                temp_path,
                margin=self.layout_item.pdf_info.cumulative_margin
            )

            self.layout_item.pdf_info.expand_boundary = True
            self.layout_item.pdf_info.expanded_filepath = expanded_path

            self.load_thumbnail()
            self.update()

            self.gui.capture_history_state(f"已扩展PDF边界 (+{margin} points，累积 {self.layout_item.pdf_info.cumulative_margin} points)")
            self.gui.statusBar().showMessage(
                f"已扩展 {self.layout_item.label} 的边界 (+{margin}，累积 {self.layout_item.pdf_info.cumulative_margin} points)"
            )

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.gui, "错误", f"扩展PDF边界失败: {e}")

    def restore_pdf_boundary(self):
        """恢复PDF原始边界"""
        try:
            import os

            if self.layout_item.pdf_info.expanded_filepath:
                try:
                    os.remove(self.layout_item.pdf_info.expanded_filepath)
                except:
                    pass

            self.layout_item.pdf_info.expand_boundary = False
            self.layout_item.pdf_info.expanded_filepath = None
            self.layout_item.pdf_info.cumulative_margin = 0

            self.load_thumbnail()
            self.update()

            self.gui.capture_history_state("已恢复PDF原始边界")
            self.gui.statusBar().showMessage(f"已恢复 {self.layout_item.label} 的PDF原始边界")

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.gui, "错误", f"恢复PDF边界失败: {e}")

    def expand_pdf_boundary_auto(self, margin, expand_left, expand_right, expand_top, expand_bottom):
        """自动扩展PDF边界 - V8 NEW 一键式操作，无需对话框"""
        try:
            from pdf_boundary_fix import expand_pdf_bounds_directional
            import tempfile
            import os

            # 删除旧的临时文件
            old_temp_path = self.layout_item.pdf_info.expanded_filepath
            if old_temp_path:
                try:
                    os.remove(old_temp_path)
                except:
                    pass

            # 创建新的临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)

            # 执行方向扩展
            expanded_path = expand_pdf_bounds_directional(
                self.layout_item.pdf_info.filepath,
                temp_path,
                margin=margin,
                expand_left=expand_left,
                expand_right=expand_right,
                expand_top=expand_top,
                expand_bottom=expand_bottom
            )

            # 更新PDF信息
            self.layout_item.pdf_info.expand_boundary = True
            self.layout_item.pdf_info.expanded_filepath = expanded_path
            self.layout_item.pdf_info.cumulative_margin = margin

            # 重新加载缩略图
            self.load_thumbnail()
            self.update()

            # 生成方向描述
            directions = []
            if expand_left: directions.append("左")
            if expand_right: directions.append("右")
            if expand_top: directions.append("上")
            if expand_bottom: directions.append("下")
            direction_str = "、".join(directions)

            self.gui.capture_history_state(f"已向{direction_str}扩展PDF边界 ({margin} points)")
            self.gui.statusBar().showMessage(
                f"已向{direction_str}扩展 {self.layout_item.label} 的边界 ({margin} points)"
            )

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.gui, "错误", f"扩展PDF边界失败: {e}")

    def shrink_pdf_boundary_auto(self, shrink_amount, shrink_left, shrink_right, shrink_top, shrink_bottom):
        """自动紧缩PDF边界 - V9 NEW 支持方向选择"""
        try:
            from pdf_boundary_fix import shrink_pdf_bounds_directional, get_whitespace_info
            import tempfile
            import os

            # 先检查是否有空白区域
            info = get_whitespace_info(self.layout_item.pdf_info.filepath)
            if info and not info['has_whitespace']:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self.gui, "提示", "该PDF周围没有可裁剪的空白区域")
                return

            # 删除旧的临时文件
            old_temp_path = self.layout_item.pdf_info.expanded_filepath
            if old_temp_path:
                try:
                    os.remove(old_temp_path)
                except:
                    pass

            # 创建新的临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)

            # 执行方向紧缩
            shrinked_path = shrink_pdf_bounds_directional(
                self.layout_item.pdf_info.filepath,
                temp_path,
                shrink_amount=shrink_amount,
                shrink_left=shrink_left,
                shrink_right=shrink_right,
                shrink_top=shrink_top,
                shrink_bottom=shrink_bottom
            )

            # 更新PDF信息
            self.layout_item.pdf_info.expand_boundary = True  # 标记为已修改
            self.layout_item.pdf_info.expanded_filepath = shrinked_path
            self.layout_item.pdf_info.cumulative_margin = -shrink_amount  # 负值表示紧缩

            # 重新加载缩略图
            self.load_thumbnail()
            self.update()

            # 生成方向描述
            directions = []
            if shrink_left: directions.append("左")
            if shrink_right: directions.append("右")
            if shrink_top: directions.append("上")
            if shrink_bottom: directions.append("下")
            direction_str = "、".join(directions)

            self.gui.capture_history_state(f"已从{direction_str}方向紧缩PDF边界 ({shrink_amount} points)")
            self.gui.statusBar().showMessage(
                f"已从{direction_str}方向紧缩 {self.layout_item.label} 的边界 ({shrink_amount} points)"
            )

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.gui, "错误", f"紧缩PDF边界失败: {e}")

    def expand_pdf_boundary_directional(self):
        """自定义方向扩展PDF边界 - V8 NEW (修复乱码：改用下拉选择)"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox, QPushButton, QLabel

        # 创建对话框
        dialog = QDialog(self.gui)
        dialog.setWindowTitle("自定义方向扩展PDF边界")
        layout = QVBoxLayout()

        # 提示信息
        info_label = QLabel("请选择要扩展的方向（可多选）：")
        layout.addWidget(info_label)

        # 方向选择复选框
        check_left = QCheckBox("← 向左扩展")
        check_left.setChecked(True)
        layout.addWidget(check_left)

        check_right = QCheckBox("→ 向右扩展")
        check_right.setChecked(True)
        layout.addWidget(check_right)

        check_top = QCheckBox("↑ 向上扩展")
        check_top.setChecked(True)
        layout.addWidget(check_top)

        check_bottom = QCheckBox("↓ 向下扩展")
        check_bottom.setChecked(True)
        layout.addWidget(check_bottom)

        # 边距设置 - V8修复：改用下拉选择避免乱码
        margin_layout = QHBoxLayout()
        margin_label = QLabel("扩展边距:")
        margin_combo = QComboBox()
        # 提供固定的边距选项（从小到大）
        margin_combo.addItems(['极小 (2点)', '很小 (5点)', '小 (10点)', '标准 (20点)',
                               '中等 (30点)', '较大 (50点)', '大 (80点)', '很大 (100点)',
                               '极大 (150点)', '最大 (200点)'])
        margin_combo.setCurrentText('标准 (20点)')  # 默认20点
        margin_layout.addWidget(margin_label)
        margin_layout.addWidget(margin_combo)
        layout.addLayout(margin_layout)

        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        # 连接按钮
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            try:
                from pdf_boundary_fix import expand_pdf_bounds_directional
                import tempfile
                import os

                # 获取用户选择
                expand_left = check_left.isChecked()
                expand_right = check_right.isChecked()
                expand_top = check_top.isChecked()
                expand_bottom = check_bottom.isChecked()

                # V8修复：从下拉框文本中提取数字
                margin_text = margin_combo.currentText()
                # 从文本"标准 (20点)"中提取20
                import re
                match = re.search(r'\((\d+)点\)', margin_text)
                if match:
                    margin = int(match.group(1))
                else:
                    margin = 20  # 默认值

                # 检查是否至少选择了一个方向
                if not (expand_left or expand_right or expand_top or expand_bottom):
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self.gui, "提示", "请至少选择一个扩展方向")
                    return

                # 删除旧的临时文件
                old_temp_path = self.layout_item.pdf_info.expanded_filepath
                if old_temp_path:
                    try:
                        os.remove(old_temp_path)
                    except:
                        pass

                # 创建新的临时文件
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)

                # 执行方向扩展
                expanded_path = expand_pdf_bounds_directional(
                    self.layout_item.pdf_info.filepath,
                    temp_path,
                    margin=margin,
                    expand_left=expand_left,
                    expand_right=expand_right,
                    expand_top=expand_top,
                    expand_bottom=expand_bottom
                )

                # 更新PDF信息
                self.layout_item.pdf_info.expand_boundary = True
                self.layout_item.pdf_info.expanded_filepath = expanded_path
                self.layout_item.pdf_info.cumulative_margin = margin

                # 重新加载缩略图
                self.load_thumbnail()
                self.update()

                # 生成方向描述
                directions = []
                if expand_left: directions.append("左")
                if expand_right: directions.append("右")
                if expand_top: directions.append("上")
                if expand_bottom: directions.append("下")
                direction_str = "、".join(directions)

                self.gui.capture_history_state(f"已向{direction_str}扩展PDF边界 ({margin} points)")
                self.gui.statusBar().showMessage(
                    f"已向{direction_str}扩展 {self.layout_item.label} 的边界 ({margin} points)"
                )

            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.gui, "错误", f"扩展PDF边界失败: {e}")

    def paint(self, painter, option, widget):
        """Custom paint to show thumbnail and selection."""
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect()

        # Draw thumbnail if available
        if self.thumbnail:
            painter.drawPixmap(rect.toRect(), self.thumbnail)

        # Draw border - V8增强：更细腻的边框线条
        if self.isSelected():
            pen = QPen(QColor(0, 120, 215), 0.6)  # 选中时0.6像素蓝色边框
            pen.setCosmetic(True)  # 确保边框不随缩放变化
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
        else:
            pen = QPen(QColor(200, 200, 200), 0.3)  # 未选中时0.3像素浅灰色边框
            pen.setCosmetic(True)  # 确保边框不随缩放变化
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

        painter.drawRect(rect)

        # Draw resize handles if selected
        if self.isSelected():
            handle_rect = QRectF(rect.width() - self.handle_size,
                                 rect.height() - self.handle_size,
                                 self.handle_size, self.handle_size)
            painter.setBrush(QBrush(QColor(0, 120, 215)))
            painter.drawRect(handle_rect)

    def update_label_position(self):
        """Position label at top-left near the figure - V9: Dynamic offset."""
        # V9 NEW: Get offset from GUI settings (default 0.7mm ≈ 2 points)
        offset = self.gui.get_label_offset() if hasattr(self.gui, 'get_label_offset') else 2
        self.label_text.setPos(-offset, -offset)

    def itemChange(self, change, value):
        """Handle item changes - V8: Grid snapping support."""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value

            # V8: Apply grid snapping if enabled
            if self.snap_to_grid and hasattr(self.gui, 'grid_size') and self.gui.snap_enabled:
                grid_size = self.gui.grid_size
                snapped_x = round(new_pos.x() / grid_size) * grid_size
                snapped_y = round(new_pos.y() / grid_size) * grid_size
                return QPointF(snapped_x, snapped_y)

            # V8: Show alignment guides
            if hasattr(self.gui, 'show_guides') and self.gui.show_guides:
                self.gui.update_alignment_guides(self)

        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        """Handle mouse press for resizing."""
        self.old_pos = QPointF(self.pos())
        self.old_rect = QRectF(self.rect())

        # Enable grid snapping during drag
        self.snap_to_grid = True

        if self.isSelected():
            pos = event.pos()
            rect = self.rect()

            handle_rect = QRectF(rect.width() - self.handle_size,
                                 rect.height() - self.handle_size,
                                 self.handle_size, self.handle_size)

            if handle_rect.contains(pos):
                self.is_resizing = True
                self.resize_start_pos = pos
                self.resize_start_rect = QRectF(self.rect())

                scene = self.scene()
                if scene:
                    selected_items = [item for item in scene.items()
                                     if isinstance(item, ResizableRectItem) and item.isSelected()]
                    if len(selected_items) > 1:
                        self.is_multi_resizing = True
                        self._multi_resize_items = selected_items
                        self._multi_resize_start_rects = {item: QRectF(item.rect()) for item in selected_items}
                        self._multi_resize_start_pos = pos
                    else:
                        self.is_multi_resizing = False

                event.accept()
                return
            else:
                self.is_resizing = False
                self.is_multi_resizing = False
        else:
            self.is_resizing = False
            self.is_multi_resizing = False

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for resizing - V8: Enhanced with scene update."""
        if self.is_resizing:
            pos = event.pos()
            delta = pos - self.resize_start_pos

            if self.is_multi_resizing:
                old_rect = self.resize_start_rect
                scale_factor = 1.0 + delta.x() / old_rect.width()
                scale_factor = max(0.1, min(5.0, scale_factor))

                for item in self._multi_resize_items:
                    start_rect = self._multi_resize_start_rects[item]
                    new_width = start_rect.width() * scale_factor
                    new_height = new_width / item.layout_item.pdf_info.aspect_ratio
                    item.setRect(0, 0, new_width, new_height)
                    item.update_label_position()
            else:
                old_rect = self.resize_start_rect
                aspect_ratio = self.layout_item.pdf_info.aspect_ratio

                new_width = max(20, old_rect.width() + delta.x())
                new_height = new_width / aspect_ratio

                self.setRect(0, 0, new_width, new_height)
                self.update_label_position()

            event.accept()

            # V8 FIX: Update scene to prevent ghosting
            if self.scene():
                self.scene().update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release and record history if geometry changed."""
        # Disable grid snapping after drag
        self.snap_to_grid = False

        # Clear alignment guides
        if hasattr(self.gui, 'clear_alignment_guides'):
            self.gui.clear_alignment_guides()

        action_desc = None

        if self.is_resizing:
            if self.is_multi_resizing:
                changed = any(
                    self._multi_resize_start_rects.get(item) != item.rect()
                    for item in self._multi_resize_items
                )
                self.is_multi_resizing = False
                self._multi_resize_items = []
                self._multi_resize_start_rects = {}
                if changed:
                    action_desc = "已缩放所选图片"
            else:
                if self.old_rect is not None:
                    new_rect = self.rect()
                    if (abs(self.old_rect.width() - new_rect.width()) > 0.01 or
                        abs(self.old_rect.height() - new_rect.height()) > 0.01):
                        action_desc = "已缩放图片"
            self.is_resizing = False
        else:
            if self.old_pos is not None:
                current_pos = self.pos()
                dx = abs(self.old_pos.x() - current_pos.x())
                dy = abs(self.old_pos.y() - current_pos.y())
                if dx > 0.01 or dy > 0.01:
                    action_desc = "已移动图片"

        if action_desc:
            self.gui.capture_history_state(action_desc)

        super().mouseReleaseEvent(event)

    def update_from_layout_item(self):
        """Update graphics item from layout item data."""
        self.setRect(0, 0, self.layout_item.width, self.layout_item.height)
        self.setPos(self.layout_item.x, self.layout_item.y)
        self.setRotation(self.layout_item.rotation)
        self.label_text.setPlainText(self.layout_item.label)
        self.update_label_position()

    def get_current_state(self) -> LayoutItem:
        """Get current layout item state from graphics item."""
        pos = self.pos()
        rect = self.rect()
        return LayoutItem(
            pdf_info=self.layout_item.pdf_info,
            x=pos.x(),
            y=pos.y(),
            width=rect.width(),
            height=rect.height(),
            rotation=self.rotation(),
            label=self.layout_item.label
        )


class ExportThread(QThread):
    """Thread for exporting PDF to avoid blocking UI."""
    progress = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, layouts, canvas_width, canvas_height, output_path, export_format='pdf', dpi=300, label_bold=True, auto_crop=False, label_offset=0.25):
        super().__init__()
        self.layouts = layouts
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.output_path = output_path
        self.export_format = export_format
        self.dpi = dpi
        self.label_bold = label_bold
        self.auto_crop = auto_crop
        self.label_offset = label_offset

    def run(self):
        try:
            if self.auto_crop and self.layouts:
                crop_width, crop_height = self._calculate_crop_dimensions()
            else:
                crop_width, crop_height = self.canvas_width, self.canvas_height

            if self.export_format == 'pdf':
                from pdf_output import export_combined_pdf
                export_combined_pdf(self.layouts, crop_width, crop_height,
                                  self.output_path, self.dpi, self.label_bold, self.label_offset)
            elif self.export_format in ['png', 'tif']:
                from pdf_output import export_combined_image
                export_combined_image(self.layouts, crop_width, crop_height,
                                    self.output_path, self.export_format, self.dpi, self.label_bold, self.label_offset)

            self.progress.emit(100)
            self.finished_signal.emit(self.output_path)
        except Exception as e:
            # V8修复：添加详细错误信息便于调试
            import traceback
            error_msg = f"{str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            self.error_signal.emit(error_msg)

    def _calculate_crop_dimensions(self):
        """Calculate the canvas size needed to fit all figures - V15 FIX."""
        if not self.layouts:
            return self.canvas_width, self.canvas_height

        max_right = 0
        max_bottom = 0

        for layout in self.layouts:
            right = layout.x + layout.width
            bottom = layout.y + layout.height
            max_right = max(max_right, right)
            max_bottom = max(max_bottom, bottom)

        margin = 2
        # V15 FIX: Use max() to ensure all figures fit within the crop area
        # Previously used min() which would crop figures extending beyond canvas
        crop_width = max(1, max_right + margin)  # At least include all figures
        crop_height = max(1, max_bottom + margin)

        return crop_width, crop_height


class FigureCombinerGUI(QMainWindow):
    """Main GUI window for figure combiner - Version 9 with multi-canvas support."""

    def __init__(self):
        super().__init__()

        # V9: Multi-canvas management
        self.canvases = []  # List of CanvasWidget instances
        self.current_canvas = None  # Currently active canvas
        self.canvas_counter = 0  # For generating canvas names

        # These will be proxies to current_canvas
        self.pdf_files = []
        self.current_layouts = []
        self.rect_items = []
        self.folder_path = ""
        self.history = HistoryManager()
        self.history_blocked = False

        # Global settings (shared across all canvases)
        self.grid_size = 5.0  # mm
        self.snap_enabled = False
        self.show_guides = False
        self.show_ruler = False
        self.guide_lines = []

        # V10 NEW: Remember last export directory
        self.last_export_dir = None

        # V16 NEW: Internal clipboard for cross-canvas copy/paste
        self.internal_clipboard = []

        # V12 NEW: Theme management (default to light theme)
        self.current_theme = "light"  # Default theme - changed to light in V12.1
        self.current_theme_class = LightTheme

        # V19: User-level defaults persisted under %USERPROFILE%/.figbox.
        self.user_settings = load_user_settings()

        # V17 NEW: figbox container temp dirs to clean up at exit
        # Each entry is the temp_dir returned by project_io.unpack_figbox /
        # import_legacy_figproj for an opened project.
        self.active_temp_dirs = []

        self.init_ui()

    def _setting(self, key, default=None):
        """Return a persisted V19 user setting with a local fallback."""
        return self.user_settings.get(key, default)

    def _set_combo_value(self, combo, value, suffix=""):
        """Set a combo text only when the target value exists."""
        text = f"{value}{suffix}"
        values = [combo.itemText(i) for i in range(combo.count())]
        if text in values:
            combo.setCurrentText(text)

    def _settings_canvas_width_text(self):
        return f"{int(self._setting('canvas_width', 297))}mm"

    def _settings_canvas_height_text(self):
        return f"{int(self._setting('canvas_height', 210))}mm"

    def _sync_to_canvas(self):
        """V15 FIX: Sync proxy variables back to current_canvas.
        
        This fixes the reference breaking issue where reassignment of proxy
        variables (like self.rect_items = []) creates new list objects,
        breaking the reference to canvas.rect_items.
        """
        if self.current_canvas:
            self.current_canvas.rect_items = self.rect_items
            self.current_canvas.pdf_files = self.pdf_files
            self.current_canvas.current_layouts = self.current_layouts
            self.current_canvas.folder_path = self.folder_path

    def init_ui(self):
        """V16: Initialize user interface with new features."""
        self.setWindowTitle("学术组图工具 V19.0 FigBox")
        self.setGeometry(50, 50, 1600, 1000)

        app_font = QFont("Microsoft YaHei", 9)
        self.setFont(app_font)

        # V11: Create menu bar
        self.create_menu_bar()

        # V9: Tab widget for multiple canvases
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_canvas_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.tabBarDoubleClicked.connect(self.rename_canvas_tab)
        self.setCentralWidget(self.tab_widget)

        # Create toolbar
        self.create_toolbar()

        # Create dockable panels
        self.create_file_list_dock()
        self.create_parameters_dock()

        # Status bar
        self.statusBar().showMessage("就绪 | V19: 智能网格与持久化设置 | 拖拽PDF到画布 | Ctrl+C复制 Ctrl+V粘贴 | Ctrl+S保存项目")

        # Setup shortcuts
        self.setup_shortcuts()

        # Enable keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)

        # V9: Create first canvas on startup
        self.create_new_canvas("画布 1")

    def create_menu_bar(self):
        """V12: Create menu bar with File and Theme menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")

        # Save project
        act_save_project = QAction("💾 保存项目...", self)
        act_save_project.setShortcut(QKeySequence("Ctrl+S"))
        act_save_project.setStatusTip("将当前画布保存为项目文件")
        act_save_project.triggered.connect(self.save_project)
        file_menu.addAction(act_save_project)

        # Open project
        act_open_project = QAction("📂 打开项目...", self)
        act_open_project.setShortcut(QKeySequence("Ctrl+O"))
        act_open_project.setStatusTip("从项目文件加载画布")
        act_open_project.triggered.connect(self.load_project)
        file_menu.addAction(act_open_project)

        file_menu.addSeparator()

        # Exit
        act_exit = QAction("❌ 退出", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.setStatusTip("退出程序")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # V12 NEW: Theme menu
        theme_menu = menubar.addMenu("主题(&T)")

        # Dark theme
        act_dark = QAction("🌙 暗黑主题", self)
        act_dark.setStatusTip("切换到暗黑专业主题")
        act_dark.triggered.connect(lambda: self.switch_theme("dark"))
        theme_menu.addAction(act_dark)

        # Light theme
        act_light = QAction("☀️ 明亮主题", self)
        act_light.setStatusTip("切换到明亮清新主题")
        act_light.triggered.connect(lambda: self.switch_theme("light"))
        theme_menu.addAction(act_light)

        # Cute theme
        act_cute = QAction("🌸 可爱主题", self)
        act_cute.setStatusTip("切换到粉色可爱主题")
        act_cute.triggered.connect(lambda: self.switch_theme("cute"))
        theme_menu.addAction(act_cute)

        settings_menu = menubar.addMenu("设置(&S)")
        act_settings = QAction("设置...", self)
        act_settings.setStatusTip("设置 V19 默认画布、边距、导出、标签和自动备份")
        act_settings.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(act_settings)

    def switch_theme(self, theme_key):
        """V12 NEW: Switch to a different theme.

        Args:
            theme_key: Theme identifier ("dark", "light", "cute")
        """
        try:
            from themes import AVAILABLE_THEMES

            if theme_key not in AVAILABLE_THEMES:
                QMessageBox.warning(self, "主题错误", f"主题 '{theme_key}' 不存在！")
                return

            # Update current theme
            self.current_theme = theme_key
            self.current_theme_class = AVAILABLE_THEMES[theme_key]

            # Apply theme to application
            app = QApplication.instance()
            if app:
                apply_theme(app, theme_key)

            # Update canvas backgrounds for all canvases
            for canvas in self.canvases:
                try:
                    if not hasattr(canvas, 'scene') or not canvas.scene:
                        continue

                    # Update scene background
                    bg_color = getattr(self.current_theme_class, 'BG_DARKEST', '#1e1e1e')
                    canvas.scene.setBackgroundBrush(QBrush(QColor(bg_color)))

                    # Get all items first (to avoid modification during iteration)
                    items_list = list(canvas.scene.items())

                    # Find and update canvas rectangle
                    border_color = getattr(self.current_theme_class, 'BORDER_LIGHT', '#3e3e42')
                    canvas_bg_color = getattr(self.current_theme_class, 'CANVAS_BG', '#1e1e1e')
                    grid_color = getattr(self.current_theme_class, 'CANVAS_GRID', '#2d2d30')

                    for item in items_list:
                        try:
                            if hasattr(item, 'is_canvas_rect') and item.is_canvas_rect:
                                item.setPen(QPen(QColor(border_color), 2, Qt.DashLine))
                                item.setBrush(QBrush(QColor(canvas_bg_color)))

                            # Update ruler lines
                            elif hasattr(item, 'is_ruler') and item.is_ruler:
                                item.setPen(QPen(QColor(grid_color), 1, Qt.DashLine))
                        except Exception as e:
                            print(f"Warning: Failed to update item: {e}")
                            continue

                except Exception as e:
                    print(f"Warning: Failed to update canvas: {e}")
                    continue

            # Show confirmation
            theme_name = getattr(self.current_theme_class, 'NAME', theme_key)
            self.statusBar().showMessage(f"✓ 已切换到 {theme_name}", 3000)

        except Exception as e:
            print(f"Error switching theme: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "主题切换错误", f"切换主题时发生错误:\n{e}")

    def create_toolbar(self):
        """Create main toolbar with three rows."""
        # First toolbar - Main operations
        toolbar1 = QToolBar("主工具栏")
        toolbar1.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar1)

        # V9: Canvas management
        act_new_canvas = QAction("➕ 新增画布", self)
        act_new_canvas.setShortcut(QKeySequence("Ctrl+T"))
        act_new_canvas.triggered.connect(lambda: self.create_new_canvas())
        toolbar1.addAction(act_new_canvas)

        toolbar1.addSeparator()

        # File operations
        act_browse = QAction("📁 浏览文件夹", self)
        act_browse.triggered.connect(self.browse_folder)
        toolbar1.addAction(act_browse)

        act_rescan = QAction("🔄 重新扫描", self)
        act_rescan.triggered.connect(self.rescan_folder)
        toolbar1.addAction(act_rescan)

        toolbar1.addSeparator()

        # V19: 智能网格 - 选中图按 行×列 排列，每行用统一系数等比缩放铺满画布宽度
        act_smart_grid = QAction("🔳 智能网格", self)
        act_smart_grid.setToolTip("选中图片按 行×列 排列。勾选「等高填充」时，点 OK 后用鼠标拖一条横线，"
                                  "选中图被缩放到同一高度铺满该宽度（等高图保持等高）；"
                                  "取消勾选则等同 V17 仅摆放、不缩放")
        act_smart_grid.triggered.connect(self.apply_smart_grid_layout)
        toolbar1.addAction(act_smart_grid)

        toolbar1.addSeparator()

        # Batch operations
        act_scale_up = QAction("🔍+ 放大", self)
        act_scale_up.triggered.connect(lambda: self.batch_scale_selected(1.05))
        toolbar1.addAction(act_scale_up)

        act_scale_down = QAction("🔍- 缩小", self)
        act_scale_down.triggered.connect(lambda: self.batch_scale_selected(0.95))
        toolbar1.addAction(act_scale_down)

        # V8 NEW: Same size buttons
        act_same_width = QAction("↔️ 等宽", self)
        act_same_width.setToolTip("将选中图片调整为相同宽度")
        act_same_width.triggered.connect(self.make_same_width)
        toolbar1.addAction(act_same_width)

        act_same_height = QAction("↕️ 等高", self)
        act_same_height.setToolTip("将选中图片调整为相同高度")
        act_same_height.triggered.connect(self.make_same_height)
        toolbar1.addAction(act_same_height)

        # Delete action
        act_delete = QAction("🗑️ 删除", self)
        act_delete.triggered.connect(self.delete_selected)
        toolbar1.addAction(act_delete)

        # Force toolbar break
        self.addToolBarBreak(Qt.TopToolBarArea)

        # Second toolbar - Alignment operations
        toolbar2 = QToolBar("对齐工具栏")
        toolbar2.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar2)

        act_align_left = QAction("⬅️ 左对齐", self)
        act_align_left.triggered.connect(self.align_selected_left)
        toolbar2.addAction(act_align_left)

        act_align_right = QAction("➡️ 右对齐", self)
        act_align_right.triggered.connect(self.align_selected_right)
        toolbar2.addAction(act_align_right)

        act_align_top = QAction("⬆️ 顶对齐", self)
        act_align_top.triggered.connect(self.align_selected_top)
        toolbar2.addAction(act_align_top)

        act_align_bottom = QAction("⬇️ 底对齐", self)
        act_align_bottom.triggered.connect(self.align_selected_bottom)
        toolbar2.addAction(act_align_bottom)

        act_align_h_center = QAction("↔️ 水平居中", self)
        act_align_h_center.triggered.connect(self.align_selected_horizontal_center)
        toolbar2.addAction(act_align_h_center)

        act_align_v_center = QAction("↕️ 垂直居中", self)
        act_align_v_center.triggered.connect(self.align_selected_vertical_center)
        toolbar2.addAction(act_align_v_center)

        toolbar2.addSeparator()

        # Distribution operations
        act_distribute_h = QAction("⟷ 水平均分", self)
        act_distribute_h.triggered.connect(self.distribute_selected_horizontal)
        toolbar2.addAction(act_distribute_h)

        act_distribute_v = QAction("⇅ 垂直均分", self)
        act_distribute_v.triggered.connect(self.distribute_selected_vertical)
        toolbar2.addAction(act_distribute_v)

        # V8 NEW: Adjust spacing
        act_adjust_spacing = QAction("📏 调整间距", self)
        act_adjust_spacing.setToolTip("批量调整选中图片之间的间距")
        act_adjust_spacing.triggered.connect(self.adjust_selected_spacing)
        toolbar2.addAction(act_adjust_spacing)

        toolbar2.addSeparator()

        # Undo/Redo
        self.act_undo = QAction("↶ 撤销", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.undo_last_action)
        toolbar2.addAction(self.act_undo)

        self.act_redo = QAction("↷ 重做", self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.redo_last_action)
        toolbar2.addAction(self.act_redo)

        # Force toolbar break
        self.addToolBarBreak(Qt.TopToolBarArea)

        # Third toolbar - Export and V8 new features
        toolbar3 = QToolBar("导出和视图工具栏")
        toolbar3.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar3)

        # Export operations
        act_preview = QAction("👁️ 预览", self)
        act_preview.triggered.connect(self.generate_preview)
        toolbar3.addAction(act_preview)

        act_export = QAction("💾 导出", self)
        act_export.triggered.connect(self.export_with_options)
        toolbar3.addAction(act_export)

        act_export_all = QAction("📦 一键导出(PDF+TIF+PNG)", self)
        act_export_all.triggered.connect(self.export_all_formats)
        toolbar3.addAction(act_export_all)

        # V11 NEW: Open export folder button
        act_open_folder = QAction("📂 打开导出位置", self)
        act_open_folder.setToolTip("打开上次导出/保存文件的文件夹")
        act_open_folder.triggered.connect(self.open_export_folder)
        toolbar3.addAction(act_open_folder)

        toolbar3.addSeparator()

        act_settings = QAction("设置", self)
        act_settings.setToolTip("打开 V19 默认设置")
        act_settings.triggered.connect(self.open_settings_dialog)
        toolbar3.addAction(act_settings)

        toolbar3.addSeparator()

        # V8 NEW: Grid snap toggle
        self.act_snap_grid = QAction("🔲 网格吸附", self)
        self.act_snap_grid.setCheckable(True)
        self.act_snap_grid.setChecked(bool(self._setting("snap_enabled", False)))
        self.snap_enabled = bool(self._setting("snap_enabled", False))
        self.act_snap_grid.setToolTip("开启后移动图片会自动吸附到网格点")
        self.act_snap_grid.triggered.connect(self.toggle_grid_snap)
        toolbar3.addAction(self.act_snap_grid)

        # V8 NEW: Show guides toggle
        self.act_show_guides = QAction("📐 对齐辅助线", self)
        self.act_show_guides.setCheckable(True)
        self.act_show_guides.setChecked(bool(self._setting("show_guides", False)))
        self.show_guides = bool(self._setting("show_guides", False))
        self.act_show_guides.setToolTip("移动图片时显示对齐辅助线")
        self.act_show_guides.triggered.connect(self.toggle_show_guides)
        toolbar3.addAction(self.act_show_guides)

        # V8 NEW: Show ruler toggle
        self.act_show_ruler = QAction("📏 标尺", self)
        self.act_show_ruler.setCheckable(True)
        self.act_show_ruler.setChecked(bool(self._setting("show_ruler", False)))
        self.show_ruler = bool(self._setting("show_ruler", False))
        self.act_show_ruler.setToolTip("显示画布标尺和参考线")
        self.act_show_ruler.triggered.connect(self.toggle_show_ruler)
        toolbar3.addAction(self.act_show_ruler)

        toolbar3.addSeparator()

        # Utilization label
        self.utilization_label = QLabel("空间利用率: 0%")
        toolbar3.addWidget(self.utilization_label)

    def create_file_list_dock(self):
        """Create dockable file list panel."""
        dock = QDockWidget("PDF文件列表", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        dock.setWidget(widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

    def create_parameters_dock(self):
        """Create dockable parameters panel with dropdown selections only."""
        dock = QDockWidget("参数设置", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Canvas settings group
        canvas_group = QGroupBox("画布设置")
        canvas_layout = QFormLayout()

        self.canvas_preset = QComboBox()
        self.canvas_preset.addItems(list(CANVAS_PRESETS.keys()))
        self._set_combo_value(self.canvas_preset, self._setting("canvas_preset", "A4横版"))
        self.canvas_preset.currentTextChanged.connect(self.on_canvas_preset_changed)
        canvas_layout.addRow("预设:", self.canvas_preset)

        self.canvas_width_combo = QComboBox()
        width_options = ['50mm', '100mm', '150mm', '180mm', '190mm', '210mm', '297mm', '400mm', '500mm']
        self.canvas_width_combo.addItems(width_options)
        self._set_combo_value(self.canvas_width_combo, int(self._setting("canvas_width", 297)), "mm")
        self.canvas_width_combo.setEditable(False)
        self.canvas_width_combo.currentTextChanged.connect(self.on_canvas_size_changed)
        canvas_layout.addRow("宽度:", self.canvas_width_combo)

        self.canvas_height_combo = QComboBox()
        height_options = ['50mm', '100mm', '150mm', '180mm', '190mm', '210mm', '297mm', '400mm', '500mm']
        self.canvas_height_combo.addItems(height_options)
        self._set_combo_value(self.canvas_height_combo, int(self._setting("canvas_height", 210)), "mm")
        self.canvas_height_combo.setEditable(False)
        self.canvas_height_combo.currentTextChanged.connect(self.on_canvas_size_changed)
        canvas_layout.addRow("高度:", self.canvas_height_combo)

        canvas_group.setLayout(canvas_layout)
        main_layout.addWidget(canvas_group)

        # Spacing settings group
        spacing_group = QGroupBox("间距设置")
        spacing_layout = QFormLayout()

        self.margin_combo = QComboBox()
        margin_options = ['0mm', '2mm', '5mm', '8mm', '10mm', '15mm', '20mm', '25mm', '30mm']
        self.margin_combo.addItems(margin_options)
        self._set_combo_value(self.margin_combo, int(self._setting("margin", 5)), "mm")
        self.margin_combo.setEditable(False)
        spacing_layout.addRow("边距:", self.margin_combo)

        self.spacing_combo = QComboBox()
        spacing_options = ['0mm', '2mm', '3mm', '5mm', '8mm', '10mm', '12mm', '15mm', '20mm']
        self.spacing_combo.addItems(spacing_options)
        self._set_combo_value(self.spacing_combo, int(self._setting("spacing", 5)), "mm")
        self.spacing_combo.setEditable(False)
        spacing_layout.addRow("间距:", self.spacing_combo)

        spacing_group.setLayout(spacing_layout)
        main_layout.addWidget(spacing_group)

        # V8 NEW: Grid settings group
        grid_group = QGroupBox("网格设置")
        grid_layout = QFormLayout()

        self.grid_size_combo = QComboBox()
        grid_options = ['1mm', '2mm', '5mm', '10mm', '20mm']
        self.grid_size_combo.addItems(grid_options)
        self._set_combo_value(self.grid_size_combo, int(self._setting("grid_size", 5)), "mm")
        self.grid_size_combo.setEditable(False)
        self.grid_size_combo.currentTextChanged.connect(self.on_grid_size_changed)
        grid_layout.addRow("网格大小:", self.grid_size_combo)

        grid_group.setLayout(grid_layout)
        main_layout.addWidget(grid_group)

        # Export settings group
        export_group = QGroupBox("导出设置")
        export_layout = QFormLayout()

        self.dpi_combo = QComboBox()
        # V16: Added 1000 DPI option
        dpi_options = ['72', '150', '300', '400', '500', '600', '1000', '1200']
        self.dpi_combo.addItems(dpi_options)
        # V19: 导出默认 1000 DPI（出版级）；屏幕预览仍用 72 DPI 渲染，保证流畅
        self._set_combo_value(self.dpi_combo, int(self._setting("dpi", 1000)))
        self.dpi_combo.setEditable(False)
        export_layout.addRow("DPI:", self.dpi_combo)

        self.export_format = QComboBox()
        self.export_format.addItems(['PDF矢量', 'PNG图片', 'TIF图片'])
        self._set_combo_value(self.export_format, self._setting("export_format", "PDF矢量"))
        export_layout.addRow("格式:", self.export_format)

        self.auto_crop_check = QCheckBox("自动裁剪空白区域")
        self.auto_crop_check.setChecked(bool(self._setting("auto_crop", True)))
        self.auto_crop_check.setToolTip("导出时自动去除底部和右侧的空白区域")
        export_layout.addRow("", self.auto_crop_check)

        export_group.setLayout(export_layout)
        main_layout.addWidget(export_group)

        # Label settings group
        label_group = QGroupBox("标签设置")
        label_layout = QFormLayout()

        self.label_fontsize_combo = QComboBox()
        fontsize_options = ['8', '10', '12', '14', '16', '18', '20']
        self.label_fontsize_combo.addItems(fontsize_options)
        self._set_combo_value(self.label_fontsize_combo, int(self._setting("label_fontsize", 12)))
        self.label_fontsize_combo.setEditable(False)
        self.label_fontsize_combo.currentTextChanged.connect(self.on_label_style_changed)
        label_layout.addRow("字号:", self.label_fontsize_combo)

        self.label_visible_check = QCheckBox("显示标签")
        self.label_visible_check.setChecked(bool(self._setting("label_visible", True)))
        self.label_visible_check.stateChanged.connect(self.on_label_style_changed)
        label_layout.addRow("", self.label_visible_check)

        self.label_bold_check = QCheckBox("加粗")
        self.label_bold_check.setChecked(bool(self._setting("label_bold", True)))
        self.label_bold_check.stateChanged.connect(self.on_label_style_changed)
        label_layout.addRow("", self.label_bold_check)

        self.label_color_combo = QComboBox()
        color_options = ['黑色', '白色', '红色', '蓝色', '绿色']
        self.label_color_combo.addItems(color_options)
        self._set_combo_value(self.label_color_combo, self._setting("label_color", "黑色"))
        self.label_color_combo.setEditable(False)
        self.label_color_combo.currentTextChanged.connect(self.on_label_style_changed)
        label_layout.addRow("颜色:", self.label_color_combo)

        # V9 NEW: Label offset/distance setting
        self.label_offset_combo = QComboBox()
        offset_options = ['0.25mm', '0.5mm', '0.7mm', '1mm', '2mm']
        self.label_offset_combo.addItems(offset_options)
        self._set_combo_value(self.label_offset_combo, self._setting("label_offset", 0.25), "mm")
        self.label_offset_combo.setEditable(False)
        self.label_offset_combo.currentTextChanged.connect(self.on_label_offset_changed)
        label_layout.addRow("距离:", self.label_offset_combo)

        label_group.setLayout(label_layout)
        main_layout.addWidget(label_group)

        main_layout.addStretch()

        dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _set_combo_without_signal(self, combo, value, suffix=""):
        """Set a combo value without triggering canvas resize side effects."""
        old_block = combo.blockSignals(True)
        self._set_combo_value(combo, value, suffix)
        combo.blockSignals(old_block)

    def _apply_saved_settings_to_controls(self):
        """Apply persisted defaults to controls without rearranging current figures."""
        self._set_combo_without_signal(self.canvas_preset, self._setting("canvas_preset", "A4横版"))
        self._set_combo_without_signal(self.canvas_width_combo, int(self._setting("canvas_width", 297)), "mm")
        self._set_combo_without_signal(self.canvas_height_combo, int(self._setting("canvas_height", 210)), "mm")
        self._set_combo_value(self.margin_combo, int(self._setting("margin", 5)), "mm")
        self._set_combo_value(self.spacing_combo, int(self._setting("spacing", 5)), "mm")
        self._set_combo_value(self.grid_size_combo, int(self._setting("grid_size", 5)), "mm")
        self.grid_size = float(self._setting("grid_size", 5))
        self._set_combo_value(self.dpi_combo, int(self._setting("dpi", 1000)))
        self._set_combo_value(self.export_format, self._setting("export_format", "PDF矢量"))
        self.auto_crop_check.setChecked(bool(self._setting("auto_crop", True)))
        self._set_combo_value(self.label_fontsize_combo, int(self._setting("label_fontsize", 12)))
        self.label_visible_check.setChecked(bool(self._setting("label_visible", True)))
        self.label_bold_check.setChecked(bool(self._setting("label_bold", True)))
        self._set_combo_value(self.label_color_combo, self._setting("label_color", "黑色"))
        self._set_combo_value(self.label_offset_combo, self._setting("label_offset", 0.25), "mm")
        self.snap_enabled = bool(self._setting("snap_enabled", False))
        self.show_guides = bool(self._setting("show_guides", False))
        self.show_ruler = bool(self._setting("show_ruler", False))
        self.act_snap_grid.setChecked(self.snap_enabled)
        self.act_show_guides.setChecked(self.show_guides)
        self.act_show_ruler.setChecked(self.show_ruler)
        self.on_label_style_changed()

    def _restart_auto_backup_from_settings(self):
        """Apply autosave settings to the running session when possible."""
        manager = getattr(self, "_backup_manager", None)
        if manager:
            manager.stop()
            self._backup_manager = None
        if not self._setting("autosave_enabled", True):
            return
        try:
            from auto_backup import AutoBackupManager
            interval = int(self._setting("autosave_interval_minutes", 5))
            manager = AutoBackupManager(self, interval_minutes=interval)
            manager.start()
            self._backup_manager = manager
        except Exception:
            logger.exception("Failed to restart autosave after settings change")

    def open_settings_dialog(self):
        """Open V19 persistent default settings dialog."""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("V19 设置")
        dialog_layout = QVBoxLayout(dialog)

        canvas_group = QGroupBox("画布默认值")
        canvas_layout = QFormLayout()
        canvas_preset = QComboBox()
        canvas_preset.addItems(list(CANVAS_PRESETS.keys()))
        self._set_combo_value(canvas_preset, self._setting("canvas_preset", "A4横版"))
        canvas_width = QComboBox()
        canvas_width.addItems(['50mm', '100mm', '150mm', '180mm', '190mm', '210mm', '297mm', '400mm', '500mm'])
        self._set_combo_value(canvas_width, int(self._setting("canvas_width", 297)), "mm")
        canvas_height = QComboBox()
        canvas_height.addItems(['50mm', '100mm', '150mm', '180mm', '190mm', '210mm', '297mm', '400mm', '500mm'])
        self._set_combo_value(canvas_height, int(self._setting("canvas_height", 210)), "mm")
        canvas_preset.currentTextChanged.connect(
            lambda name: (
                canvas_width.setCurrentText(f"{int(CANVAS_PRESETS[name][0])}mm"),
                canvas_height.setCurrentText(f"{int(CANVAS_PRESETS[name][1])}mm")
            ) if name in CANVAS_PRESETS and CANVAS_PRESETS[name] else None
        )
        canvas_layout.addRow("预设:", canvas_preset)
        canvas_layout.addRow("宽度:", canvas_width)
        canvas_layout.addRow("高度:", canvas_height)
        canvas_group.setLayout(canvas_layout)
        dialog_layout.addWidget(canvas_group)

        layout_group = QGroupBox("布局默认值")
        layout_form = QFormLayout()
        margin = QComboBox()
        margin.addItems(['0mm', '2mm', '5mm', '8mm', '10mm', '15mm', '20mm', '25mm', '30mm'])
        self._set_combo_value(margin, int(self._setting("margin", 5)), "mm")
        spacing = QComboBox()
        spacing.addItems(['0mm', '2mm', '3mm', '5mm', '8mm', '10mm', '12mm', '15mm', '20mm'])
        self._set_combo_value(spacing, int(self._setting("spacing", 5)), "mm")
        grid_size = QComboBox()
        grid_size.addItems(['1mm', '2mm', '5mm', '10mm', '20mm'])
        self._set_combo_value(grid_size, int(self._setting("grid_size", 5)), "mm")
        layout_form.addRow("边距:", margin)
        layout_form.addRow("图间距:", spacing)
        layout_form.addRow("网格:", grid_size)
        layout_group.setLayout(layout_form)
        dialog_layout.addWidget(layout_group)

        export_group = QGroupBox("导出默认值")
        export_form = QFormLayout()
        dpi = QComboBox()
        dpi.addItems(['72', '150', '300', '400', '500', '600', '1000', '1200'])
        self._set_combo_value(dpi, int(self._setting("dpi", 1000)))
        export_format = QComboBox()
        export_format.addItems(['PDF矢量', 'PNG图片', 'TIF图片'])
        self._set_combo_value(export_format, self._setting("export_format", "PDF矢量"))
        auto_crop = QCheckBox("自动裁剪空白区域")
        auto_crop.setChecked(bool(self._setting("auto_crop", True)))
        export_form.addRow("DPI:", dpi)
        export_form.addRow("格式:", export_format)
        export_form.addRow("", auto_crop)
        export_group.setLayout(export_form)
        dialog_layout.addWidget(export_group)

        label_group = QGroupBox("标签默认值")
        label_form = QFormLayout()
        label_fontsize = QComboBox()
        label_fontsize.addItems(['8', '10', '12', '14', '16', '18', '20'])
        self._set_combo_value(label_fontsize, int(self._setting("label_fontsize", 12)))
        label_visible = QCheckBox("显示标签")
        label_visible.setChecked(bool(self._setting("label_visible", True)))
        label_bold = QCheckBox("加粗")
        label_bold.setChecked(bool(self._setting("label_bold", True)))
        label_color = QComboBox()
        label_color.addItems(['黑色', '白色', '红色', '蓝色', '绿色'])
        self._set_combo_value(label_color, self._setting("label_color", "黑色"))
        label_offset = QComboBox()
        label_offset.addItems(['0.25mm', '0.5mm', '0.7mm', '1mm', '2mm'])
        self._set_combo_value(label_offset, self._setting("label_offset", 0.25), "mm")
        label_form.addRow("字号:", label_fontsize)
        label_form.addRow("", label_visible)
        label_form.addRow("", label_bold)
        label_form.addRow("颜色:", label_color)
        label_form.addRow("距离:", label_offset)
        label_group.setLayout(label_form)
        dialog_layout.addWidget(label_group)

        view_group = QGroupBox("视图与自动备份")
        view_form = QFormLayout()
        snap_enabled = QCheckBox("默认开启网格吸附")
        snap_enabled.setChecked(bool(self._setting("snap_enabled", False)))
        show_guides = QCheckBox("默认显示对齐辅助线")
        show_guides.setChecked(bool(self._setting("show_guides", False)))
        show_ruler = QCheckBox("默认显示标尺")
        show_ruler.setChecked(bool(self._setting("show_ruler", False)))
        autosave_enabled = QCheckBox("开启自动备份")
        autosave_enabled.setChecked(bool(self._setting("autosave_enabled", True)))
        autosave_interval = QSpinBox()
        autosave_interval.setRange(1, 60)
        autosave_interval.setValue(int(self._setting("autosave_interval_minutes", 5)))
        view_form.addRow("", snap_enabled)
        view_form.addRow("", show_guides)
        view_form.addRow("", show_ruler)
        view_form.addRow("", autosave_enabled)
        view_form.addRow("备份间隔(分钟):", autosave_interval)
        view_group.setLayout(view_form)
        dialog_layout.addWidget(view_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)

        if dialog.exec_() != QDialog.Accepted:
            return

        new_settings = {
            "theme": self.current_theme,
            "canvas_preset": canvas_preset.currentText(),
            "canvas_width": self._get_value_from_combo(canvas_width.currentText()),
            "canvas_height": self._get_value_from_combo(canvas_height.currentText()),
            "margin": self._get_value_from_combo(margin.currentText()),
            "spacing": self._get_value_from_combo(spacing.currentText()),
            "grid_size": self._get_value_from_combo(grid_size.currentText()),
            "dpi": int(dpi.currentText()),
            "export_format": export_format.currentText(),
            "auto_crop": auto_crop.isChecked(),
            "label_fontsize": int(label_fontsize.currentText()),
            "label_visible": label_visible.isChecked(),
            "label_bold": label_bold.isChecked(),
            "label_color": label_color.currentText(),
            "label_offset": float(label_offset.currentText().replace("mm", "").strip()),
            "snap_enabled": snap_enabled.isChecked(),
            "show_guides": show_guides.isChecked(),
            "show_ruler": show_ruler.isChecked(),
            "autosave_enabled": autosave_enabled.isChecked(),
            "autosave_interval_minutes": autosave_interval.value(),
        }
        self.user_settings = save_settings(new_settings)
        self._apply_saved_settings_to_controls()
        self._restart_auto_backup_from_settings()
        self.statusBar().showMessage("V19 设置已保存", 5000)

    def _get_value_from_combo(self, combo_text):
        """Extract numeric value from combo box text like '10mm' -> 10."""
        return int(combo_text.replace('mm', '').strip())

    def get_canvas_width(self):
        """Get canvas width value from combo box."""
        return self._get_value_from_combo(self.canvas_width_combo.currentText())

    def get_canvas_height(self):
        """Get canvas height value from combo box."""
        return self._get_value_from_combo(self.canvas_height_combo.currentText())

    def get_active_canvas_width(self):
        """Get the real width of the current tab's canvas."""
        if self.current_canvas is not None:
            return self.current_canvas.canvas_width
        return self.get_canvas_width()

    def get_active_canvas_height(self):
        """Get the real height of the current tab's canvas."""
        if self.current_canvas is not None:
            return self.current_canvas.canvas_height
        return self.get_canvas_height()

    def get_margin(self):
        """Get margin value from combo box."""
        return self._get_value_from_combo(self.margin_combo.currentText())

    def get_spacing(self):
        """Get spacing value from combo box."""
        return self._get_value_from_combo(self.spacing_combo.currentText())

    def get_dpi(self):
        """Get DPI value from combo box."""
        return int(self.dpi_combo.currentText())

    def get_label_fontsize(self):
        """Get label font size from combo box."""
        return int(self.label_fontsize_combo.currentText())

    def get_label_color(self):
        """Get label color from combo box."""
        color_map = {
            '黑色': QColor(0, 0, 0),
            '白色': QColor(255, 255, 255),
            '红色': QColor(255, 0, 0),
            '蓝色': QColor(0, 0, 255),
            '绿色': QColor(0, 128, 0)
        }
        return color_map.get(self.label_color_combo.currentText(), QColor(0, 0, 0))

    def is_label_visible(self):
        """Check if labels should be visible."""
        return self.label_visible_check.isChecked()

    def is_label_bold(self):
        """Check if labels should be bold."""
        return self.label_bold_check.isChecked()

    def get_label_offset(self):
        """Get label offset/distance from combo box - V9 NEW."""
        # V9 FIX: Use float() for decimal values like 0.7mm
        return float(self.label_offset_combo.currentText().replace('mm', '').strip())

    def is_auto_crop(self):
        """Check if auto crop is enabled."""
        return self.auto_crop_check.isChecked()

    def on_label_style_changed(self):
        """Handle label style changes."""
        fontsize = self.get_label_fontsize()
        color = self.get_label_color()
        visible = self.is_label_visible()
        bold = self.is_label_bold()

        for item in self.rect_items:
            font_weight = QFont.Bold if bold else QFont.Normal
            font = QFont("Arial", fontsize, font_weight)
            item.label_text.setFont(font)
            item.label_text.setDefaultTextColor(color)
            item.label_text.setVisible(visible)

    def on_label_offset_changed(self, text):
        """Handle label offset/distance change - V9 NEW."""
        # Update all existing labels
        for item in self.rect_items:
            item.update_label_position()

    def on_grid_size_changed(self, text):
        """Handle grid size change - V8 NEW."""
        self.grid_size = self._get_value_from_combo(text)

    def on_canvas_preset_changed(self, preset_name):
        """Handle canvas preset change."""
        if preset_name in CANVAS_PRESETS:
            size = CANVAS_PRESETS[preset_name]
            if size:
                self.canvas_width_combo.setCurrentText(f'{int(size[0])}mm')
                self.canvas_height_combo.setCurrentText(f'{int(size[1])}mm')

    def on_canvas_size_changed(self):
        """Handle canvas size change - V8 NEW: Update canvas when size changes."""
        # Update canvas rectangle to match new size
        self.update_canvas_rectangle()
        # Update ruler if enabled
        if self.show_ruler:
            self.update_ruler_display()

    def initialize_empty_canvas(self):
        """Initialize empty canvas on startup - V8 NEW, V15 FIX."""
        # Clear the scene
        self.scene.clear()
        # V15 FIX: Use clear() instead of = [] to maintain list reference
        self.rect_items.clear()
        self.current_layouts.clear()
        # V15 FIX: Sync back to canvas to ensure consistency
        self._sync_to_canvas()

        # V12: Create canvas rectangle with current theme colors
        canvas_rect = QGraphicsRectItem(0, 0, self.get_canvas_width(), self.get_canvas_height())
        canvas_rect.setPen(QPen(QColor(self.current_theme_class.BORDER_LIGHT), 2, Qt.DashLine))
        canvas_rect.setBrush(QBrush(QColor(self.current_theme_class.CANVAS_BG)))
        canvas_rect.setZValue(-1000)
        canvas_rect.is_canvas_rect = True  # Mark as canvas rectangle
        self.scene.addItem(canvas_rect)

        # Fit view to canvas
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

        # Initialize empty history
        self.history.reset([])

        # Update status
        self.statusBar().showMessage("就绪 | 可直接拖拽PDF文件到画布中 | V8新功能: 方向键移动，旋转，智能对齐 | F11全屏 | Ctrl+Z撤销")

    def update_canvas_rectangle(self):
        """Update canvas rectangle size - V8 NEW."""
        # Find and update canvas rectangle
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, 'is_canvas_rect'):
                item.setRect(0, 0, self.get_canvas_width(), self.get_canvas_height())
                self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
                self.statusBar().showMessage(f"画布已更新: {self.get_canvas_width()}mm × {self.get_canvas_height()}mm")
                return

    # V9: Multi-canvas management methods
    def create_new_canvas(self, canvas_name=None):
        """Create a new canvas tab - V9 NEW."""
        if canvas_name is None:
            self.canvas_counter += 1
            canvas_name = f"画布 {self.canvas_counter}"

        # Create canvas widget
        canvas = CanvasWidget(
            self,
            canvas_name,
            self.get_canvas_width(),
            self.get_canvas_height()
        )

        # V12: Create scene and view with current theme
        scene = QGraphicsScene()
        scene.setBackgroundBrush(QBrush(QColor(self.current_theme_class.BG_DARKEST)))
        view = CanvasView()
        view.setScene(scene)
        view.main_window = self

        # V11 FIX: Set larger scene rect to allow scrolling beyond canvas
        # Make scene 2x larger than canvas to allow scrolling
        margin = max(canvas.canvas_width, canvas.canvas_height) * 0.5
        scene.setSceneRect(-margin, -margin,
                          canvas.canvas_width + 2 * margin,
                          canvas.canvas_height + 2 * margin)

        # Store references in canvas
        canvas.scene = scene
        canvas.view = view

        # V12: Initialize empty canvas with current theme
        canvas_rect = QGraphicsRectItem(0, 0, canvas.canvas_width, canvas.canvas_height)
        canvas_rect.setPen(QPen(QColor(self.current_theme_class.BORDER_LIGHT), 2, Qt.DashLine))
        canvas_rect.setBrush(QBrush(QColor(self.current_theme_class.CANVAS_BG)))
        canvas_rect.setZValue(-1000)
        canvas_rect.is_canvas_rect = True
        scene.addItem(canvas_rect)

        # V11 FIX: Fit view to canvas (not just center)
        # This makes the canvas fill the view while still allowing scrolling beyond bounds
        view.fitInView(canvas_rect, Qt.KeepAspectRatio)

        # Initialize history
        canvas.history.reset([])

        # Add canvas to list
        self.canvases.append(canvas)

        # Add tab
        tab_index = self.tab_widget.addTab(view, canvas.get_display_name())
        self.tab_widget.setCurrentIndex(tab_index)

        # V14 FIX: Force sync state to new canvas to avoid timing issues
        self.current_canvas = canvas
        self.scene = canvas.scene
        self.view = canvas.view
        self.pdf_files = canvas.pdf_files
        self.current_layouts = canvas.current_layouts
        self.rect_items = canvas.rect_items
        self.folder_path = canvas.folder_path
        self.history = canvas.history

        # Update status
        self.statusBar().showMessage(f"已创建新画布: {canvas_name}")

        return canvas

    def close_canvas_tab(self, index):
        """Close a canvas tab - V11: Enhanced with save option."""
        if len(self.canvases) <= 1:
            QMessageBox.information(self, "提示", "至少需要保留一个画布")
            return

        canvas = self.canvases[index]

        # V11 NEW: Check for unsaved changes and offer save option
        if canvas.has_unsaved_changes():
            # Create custom message box with Save, Don't Save, Cancel options
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("保存画布")
            msg.setText(f"画布 '{canvas.canvas_name}' 有未保存的内容")
            msg.setInformativeText("是否要保存此画布？")

            # Add custom buttons
            save_btn = msg.addButton("保存", QMessageBox.AcceptRole)
            dont_save_btn = msg.addButton("不保存", QMessageBox.DestructiveRole)
            cancel_btn = msg.addButton("取消", QMessageBox.RejectRole)

            msg.setDefaultButton(save_btn)
            msg.exec_()

            clicked = msg.clickedButton()

            if clicked == cancel_btn:
                # User cancelled, don't close
                return
            elif clicked == save_btn:
                # Save before closing
                # Switch to this canvas first
                self.tab_widget.setCurrentIndex(index)
                # Call save_project
                self.save_project()
                # Check if save was successful (user might have cancelled save dialog)
                # For now, we'll continue closing

        # Remove tab and canvas
        self.tab_widget.removeTab(index)
        self.canvases.pop(index)

        self.statusBar().showMessage(f"已关闭画布: {canvas.canvas_name}")

    def on_tab_changed(self, index):
        """Handle tab change - V9 NEW."""
        if index < 0 or index >= len(self.canvases):
            return

        # Get the new current canvas
        canvas = self.canvases[index]
        self.current_canvas = canvas

        # Update proxies to point to current canvas
        self.scene = canvas.scene
        self.view = canvas.view
        self.pdf_files = canvas.pdf_files
        self.current_layouts = canvas.current_layouts
        self.rect_items = canvas.rect_items
        self.folder_path = canvas.folder_path
        self.history = canvas.history

        # Update file list
        self.file_list.clear()
        for pdf in canvas.pdf_files:
            orientation = "竖图" if pdf.is_tall else "横图" if pdf.is_wide else "方图"
            item_text = f"{pdf.filename}\n  {pdf.width:.0f}x{pdf.height:.0f} pt | {orientation}"
            item = QListWidgetItem(item_text)
            self.file_list.addItem(item)

        # Update history buttons
        self.update_history_actions()

        # Update status
        self.statusBar().showMessage(f"已切换到: {canvas.canvas_name} | {len(canvas.pdf_files)} 个PDF")

    def rename_canvas_tab(self, index):
        """Rename a canvas tab - V9 NEW."""
        if index < 0 or index >= len(self.canvases):
            return

        canvas = self.canvases[index]
        new_name, ok = QInputDialog.getText(
            self, "重命名画布",
            "请输入新的画布名称:",
            text=canvas.canvas_name
        )

        if ok and new_name:
            canvas.canvas_name = new_name
            self.tab_widget.setTabText(index, canvas.get_display_name())
            self.statusBar().showMessage(f"已重命名画布为: {new_name}")

    def setup_shortcuts(self):
        """Setup keyboard shortcuts - V16: Added copy/paste for cross-canvas functionality."""
        from PyQt5.QtWidgets import QShortcut

        # Fullscreen
        shortcut_fullscreen = QShortcut(QKeySequence("F11"), self)
        shortcut_fullscreen.activated.connect(self.toggle_fullscreen)

        # Delete
        shortcut_delete = QShortcut(QKeySequence.Delete, self)
        shortcut_delete.activated.connect(self.delete_selected)

        # V16 NEW: Copy/Paste for cross-canvas functionality
        shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        shortcut_copy.activated.connect(self.copy_selected_items)

        shortcut_paste = QShortcut(QKeySequence("Ctrl+V"), self)
        shortcut_paste.activated.connect(self.paste_items)

    def keyPressEvent(self, event):
        """Handle key press events - V8 NEW: Arrow keys for movement."""
        # Arrow keys to move selected items
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self.move_selected_with_arrow_keys(event.key())
            event.accept()
        else:
            super().keyPressEvent(event)

    def move_selected_with_arrow_keys(self, key):
        """Move selected items with arrow keys - V8 NEW.

        Args:
            key: Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, or Qt.Key_Down
        """
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if not selected_items:
            return

        # Determine move distance (1mm or 10mm with Shift)
        move_distance = 10.0 if QApplication.keyboardModifiers() & Qt.ShiftModifier else 1.0

        # Calculate movement delta
        dx = 0.0
        dy = 0.0

        if key == Qt.Key_Left:
            dx = -move_distance
        elif key == Qt.Key_Right:
            dx = move_distance
        elif key == Qt.Key_Up:
            dy = -move_distance
        elif key == Qt.Key_Down:
            dy = move_distance

        # Move all selected items
        for item in selected_items:
            current_pos = item.pos()
            new_pos = QPointF(current_pos.x() + dx, current_pos.y() + dy)
            item.setPos(new_pos)

        # Capture history
        direction = {Qt.Key_Left: "左", Qt.Key_Right: "右",
                    Qt.Key_Up: "上", Qt.Key_Down: "下"}[key]
        self.capture_history_state(f"已向{direction}移动图片 {move_distance}mm")
        self.statusBar().showMessage(f"已向{direction}移动 {len(selected_items)} 个图片 {move_distance}mm")

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):
        """V16 NEW: Handle close event with confirmation dialog.

        Args:
            event: QCloseEvent
        """
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出学术组图工具吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # V17: Clean up any extracted figbox temp dirs
            for td in list(self.active_temp_dirs):
                pio.cleanup_temp_dir(td)
            self.active_temp_dirs.clear()
            event.accept()  # Close the application
        else:
            event.ignore()  # Keep the application open

    def toggle_grid_snap(self, checked):
        """Toggle grid snapping - V8 NEW."""
        self.snap_enabled = checked
        status = "已开启" if checked else "已关闭"
        self.statusBar().showMessage(f"网格吸附{status} (网格大小: {self.grid_size}mm)")

    def toggle_show_guides(self, checked):
        """Toggle alignment guides - V8 NEW."""
        self.show_guides = checked
        if not checked:
            self.clear_alignment_guides()
        status = "已开启" if checked else "已关闭"
        self.statusBar().showMessage(f"对齐辅助线{status}")

    def toggle_show_ruler(self, checked):
        """Toggle ruler display - V8 NEW."""
        self.show_ruler = checked
        self.update_ruler_display()
        status = "已显示" if checked else "已隐藏"
        self.statusBar().showMessage(f"标尺{status}")

    def update_ruler_display(self):
        """Update ruler display on canvas - V8 NEW."""
        # Remove existing ruler lines
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and hasattr(item, 'is_ruler'):
                self.scene.removeItem(item)

        if not self.show_ruler:
            return

        # Draw ruler lines
        canvas_width = self.get_canvas_width()
        canvas_height = self.get_canvas_height()

        # V12: Horizontal ruler lines with current theme colors
        for y in range(0, int(canvas_height) + 1, 10):
            line = QGraphicsLineItem(0, y, canvas_width, y)
            line.setPen(QPen(QColor(self.current_theme_class.CANVAS_GRID), 1, Qt.DashLine))
            line.is_ruler = True
            line.setZValue(-500)
            self.scene.addItem(line)

        # V12: Vertical ruler lines with current theme colors
        for x in range(0, int(canvas_width) + 1, 10):
            line = QGraphicsLineItem(x, 0, x, canvas_height)
            line.setPen(QPen(QColor(self.current_theme_class.CANVAS_GRID), 1, Qt.DashLine))
            line.is_ruler = True
            line.setZValue(-500)
            self.scene.addItem(line)

    def update_alignment_guides(self, moving_item):
        """Update alignment guide lines - V8 NEW.

        Args:
            moving_item: The item being moved
        """
        if not self.show_guides:
            return

        self.clear_alignment_guides()

        # Get moving item bounds
        moving_rect = moving_item.sceneBoundingRect()
        moving_left = moving_rect.left()
        moving_right = moving_rect.right()
        moving_top = moving_rect.top()
        moving_bottom = moving_rect.bottom()
        moving_h_center = moving_rect.center().x()
        moving_v_center = moving_rect.center().y()

        # Check alignment with other items
        threshold = 2.0  # mm

        for item in self.rect_items:
            if item == moving_item or not isinstance(item, ResizableRectItem):
                continue

            item_rect = item.sceneBoundingRect()
            item_left = item_rect.left()
            item_right = item_rect.right()
            item_top = item_rect.top()
            item_bottom = item_rect.bottom()
            item_h_center = item_rect.center().x()
            item_v_center = item_rect.center().y()

            # Check vertical alignments
            if abs(moving_left - item_left) < threshold:
                self.draw_guide_line(moving_left, 0, moving_left, self.get_canvas_height())
            if abs(moving_right - item_right) < threshold:
                self.draw_guide_line(moving_right, 0, moving_right, self.get_canvas_height())
            if abs(moving_h_center - item_h_center) < threshold:
                self.draw_guide_line(moving_h_center, 0, moving_h_center, self.get_canvas_height())

            # Check horizontal alignments
            if abs(moving_top - item_top) < threshold:
                self.draw_guide_line(0, moving_top, self.get_canvas_width(), moving_top)
            if abs(moving_bottom - item_bottom) < threshold:
                self.draw_guide_line(0, moving_bottom, self.get_canvas_width(), moving_bottom)
            if abs(moving_v_center - item_v_center) < threshold:
                self.draw_guide_line(0, moving_v_center, self.get_canvas_width(), moving_v_center)

    def draw_guide_line(self, x1, y1, x2, y2):
        """Draw an alignment guide line - V8 NEW."""
        line = QGraphicsLineItem(x1, y1, x2, y2)
        line.setPen(QPen(QColor(255, 0, 0, 150), 1, Qt.DashLine))
        line.setZValue(1000)
        self.guide_lines.append(line)
        self.scene.addItem(line)

    def clear_alignment_guides(self):
        """Clear all alignment guide lines - V8 NEW."""
        for line in self.guide_lines:
            self.scene.removeItem(line)
        self.guide_lines = []

    def make_same_width(self):
        """Make selected items have the same width - V9: Use maximum width as reference."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片")
            return

        # V9 NEW: Use the maximum width as reference (以最宽的图为准)
        reference_width = max(item.rect().width() for item in selected_items)

        for item in selected_items:
            old_rect = item.rect()
            aspect_ratio = item.layout_item.pdf_info.aspect_ratio
            new_height = reference_width / aspect_ratio
            item.setRect(0, 0, reference_width, new_height)
            item.update_label_position()

        self.capture_history_state(f"已将 {len(selected_items)} 个图片调整为等宽（以最宽图为准）")
        self.statusBar().showMessage(f"已将 {len(selected_items)} 个图片调整为等宽: {reference_width:.1f}mm（以最宽图为准）")

    def make_same_height(self):
        """Make selected items have the same height - V9: Use maximum height as reference."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片")
            return

        # V9 NEW: Use the maximum height as reference (以最高的图为准)
        reference_height = max(item.rect().height() for item in selected_items)

        for item in selected_items:
            old_rect = item.rect()
            aspect_ratio = item.layout_item.pdf_info.aspect_ratio
            new_width = reference_height * aspect_ratio
            item.setRect(0, 0, new_width, reference_height)
            item.update_label_position()

        self.capture_history_state(f"已将 {len(selected_items)} 个图片调整为等高（以最高图为准）")
        self.statusBar().showMessage(f"已将 {len(selected_items)} 个图片调整为等高: {reference_height:.1f}mm（以最高图为准）")

    def adjust_selected_spacing(self):
        """Adjust spacing between selected items - V8 NEW."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片")
            return

        # Ask user for desired spacing - V8修复：改用下拉选择避免乱码
        spacing_options = ['无间距 (0mm)', '很小 (2mm)', '小 (3mm)', '标准 (5mm)',
                          '中等 (8mm)', '较大 (10mm)', '大 (12mm)', '很大 (15mm)', '最大 (20mm)']
        spacing_text, ok = QInputDialog.getItem(
            self, "调整间距",
            "请选择图片之间的间距:",
            spacing_options,
            3,  # 默认选择"标准 (5mm)"
            False
        )

        if not ok:
            return

        # V8修复：从下拉框文本中提取数字
        import re
        match = re.search(r'\((\d+)mm\)', spacing_text)
        if match:
            spacing = float(match.group(1))
        else:
            spacing = 5.0  # 默认值

        # Ask for distribution direction
        direction, ok = QInputDialog.getItem(
            self, "选择方向",
            "请选择分布方向:",
            ["水平", "垂直"],
            0, False
        )

        if not ok:
            return

        if direction == "水平":
            # Sort by x position
            selected_items.sort(key=lambda item: item.pos().x())

            current_x = selected_items[0].pos().x() + selected_items[0].rect().width()

            for i, item in enumerate(selected_items[1:], 1):
                new_x = current_x + spacing
                item.setPos(new_x, item.pos().y())
                current_x = new_x + item.rect().width()
        else:  # 垂直
            # Sort by y position
            selected_items.sort(key=lambda item: item.pos().y())

            current_y = selected_items[0].pos().y() + selected_items[0].rect().height()

            for i, item in enumerate(selected_items[1:], 1):
                new_y = current_y + spacing
                item.setPos(item.pos().x(), new_y)
                current_y = new_y + item.rect().height()

        self.capture_history_state(f"已调整图片间距为 {spacing}mm")
        self.statusBar().showMessage(f"已将 {len(selected_items)} 个图片{direction}间距调整为 {spacing}mm")

    def import_dropped_pdfs(self, pdf_paths, drop_pos=None, original_paths=None):
        """Import PDF files dropped onto the canvas - V8 NEW.

        Args:
            pdf_paths: List of PDF file paths
            drop_pos: V19 - 拖放落点 (x_mm, y_mm)，图的中心落在此处；None 则居中
            original_paths: 可选映射，临时 PDF 路径 -> 用户最早导入的真实路径
        """
        try:
            imported_count = 0
            original_paths = original_paths or {}

            for pdf_path in pdf_paths:
                if not os.path.exists(pdf_path):
                    continue

                # Open PDF and get info
                doc = fitz.open(pdf_path)
                if len(doc) == 0:
                    doc.close()
                    continue

                page = doc[0]
                rect = page.rect
                width = rect.width
                height = rect.height
                aspect_ratio = width / height if height > 0 else 1.0

                original_path = original_paths.get(pdf_path, pdf_path)
                filename = os.path.basename(original_path)

                # Create PDF info
                from pdf_utils import parse_filename
                sort_key = parse_filename(filename)

                pdf_info = PDFInfo(
                    filepath=pdf_path,
                    filename=filename,
                    width=width,
                    height=height,
                    aspect_ratio=aspect_ratio,
                    sort_key=sort_key,
                    original_path=original_path,
                )

                # Add to pdf_files list
                self.pdf_files.append(pdf_info)

                # Create layout item at center of canvas
                # Scale to reasonable size (e.g., 1/4 of canvas width)
                target_width = self.get_canvas_width() / 4
                scale = target_width / points_to_mm(width)
                layout_width = points_to_mm(width) * scale
                layout_height = points_to_mm(height) * scale

                # V19: 落在拖放位置（图的中心对准落点）；多张时依次错开避免完全重叠。
                # 未提供落点（如剪贴板粘贴）则居中。
                if drop_pos is not None:
                    cascade = imported_count * 5.0  # mm
                    layout_x = drop_pos[0] - layout_width / 2 + cascade
                    layout_y = drop_pos[1] - layout_height / 2 + cascade
                else:
                    layout_x = (self.get_canvas_width() - layout_width) / 2
                    layout_y = (self.get_canvas_height() - layout_height) / 2

                # Generate label (next available letter)
                label = chr(65 + len(self.current_layouts))

                layout_item = LayoutItem(
                    pdf_info=pdf_info,
                    x=layout_x,
                    y=layout_y,
                    width=layout_width,
                    height=layout_height,
                    rotation=0,
                    label=label
                )

                # Add to current layouts
                self.current_layouts.append(layout_item)

                # Create graphics item
                rect_item = ResizableRectItem(layout_item, self)
                self._apply_label_style(rect_item)
                self.scene.addItem(rect_item)
                self.rect_items.append(rect_item)

                # Add to file list
                orientation = "竖图" if pdf_info.is_tall else "横图" if pdf_info.is_wide else "方图"
                item_text = f"{pdf_info.filename}\n  {pdf_info.width:.0f}x{pdf_info.height:.0f} pt | {orientation}"
                list_item = QListWidgetItem(item_text)
                self.file_list.addItem(list_item)

                imported_count += 1
                doc.close()

            if imported_count > 0:
                self.capture_history_state(f"已导入 {imported_count} 个PDF文件")
                self.statusBar().showMessage(f"成功导入 {imported_count} 个PDF文件")
            else:
                self.statusBar().showMessage("未能导入任何PDF文件")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入PDF失败: {e}")

    def import_dropped_files(self, file_paths, drop_pos=None):
        """V10 NEW: Import PDF and image files dropped onto the canvas.

        Supports PDF, TIF, TIFF, PNG, JPG, JPEG formats.
        Image files are converted to temporary PDFs for processing.

        Args:
            file_paths: List of file paths (PDF or image files)
            drop_pos: V19 - 拖放落点 (x_mm, y_mm)，图将落在此处；None 则居中
        """
        try:
            pdf_files = []
            temp_pdfs = []  # Track temporary PDFs for cleanup
            original_paths = {}

            for filepath in file_paths:
                if not os.path.exists(filepath):
                    continue

                ext = os.path.splitext(filepath)[1].lower()

                if ext == '.pdf':
                    pdf_files.append(filepath)
                    original_paths[filepath] = filepath
                elif ext in ('.tif', '.tiff', '.png', '.jpg', '.jpeg'):
                    # Convert image to temporary PDF
                    temp_pdf = self._convert_image_to_pdf(filepath)
                    if temp_pdf:
                        pdf_files.append(temp_pdf)
                        temp_pdfs.append(temp_pdf)
                        original_paths[temp_pdf] = filepath

            if pdf_files:
                self.import_dropped_pdfs(pdf_files, drop_pos=drop_pos, original_paths=original_paths)
            else:
                self.statusBar().showMessage("未能导入任何文件")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入文件失败: {e}")

    def _convert_image_to_pdf(self, image_path):
        """V10 NEW: Convert an image file to a temporary PDF.

        Args:
            image_path: Path to image file (TIF/PNG/JPG)

        Returns:
            Path to temporary PDF file, or None if conversion fails
        """
        try:
            from PIL import Image
            import tempfile

            # Open image
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else img.split()[1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create temporary PDF file
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_pdf.close()

            # Save as PDF
            img.save(temp_pdf.name, 'PDF', resolution=300.0)

            return temp_pdf.name

        except Exception as e:
            print(f"转换图片 {image_path} 到PDF失败: {e}")
            return None

    def paste_from_clipboard(self):
        """V10 NEW: Paste PDF and image files from clipboard.

        Supports pasting PDF and image files that were copied in file explorer.
        """
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()

            if mime_data.hasUrls():
                files = []
                supported_exts = ('.pdf', '.tif', '.tiff', '.png', '.jpg', '.jpeg')
                for url in mime_data.urls():
                    filepath = url.toLocalFile()
                    if filepath.lower().endswith(supported_exts):
                        files.append(filepath)

                if files:
                    self.import_dropped_files(files)
                else:
                    self.statusBar().showMessage("剪贴板中没有支持的文件（PDF/TIF/PNG/JPG）")
            else:
                self.statusBar().showMessage("剪贴板中没有文件")

        except Exception as e:
            QMessageBox.warning(self, "警告", f"粘贴失败: {e}")

    def renumber_labels(self):
        """V19: 按"现有标签顺序"重新编号为连续 A、B、C…（删除后保持顺序与连续性）。"""
        ordered = sorted(self.rect_items,
                         key=lambda it: self._label_rank(it.layout_item.label))
        for idx, item in enumerate(ordered):
            new_label = chr(65 + idx)
            item.layout_item.label = new_label
            item.label_text.setPlainText(new_label)

    def relabel_insert(self, moved_item, new_label):
        """V19 标签级联：把 moved_item 移动到 new_label 所在的位置，其余标签自动顺延。

        例：A B C D，把 C 改成 B → A C B D（原 B 顺延为 C）；
            插入一张图并设为 B → 原 B C D 顺延为 C D E。
        始终保持所有标签为连续的 A、B、C…
        """
        old_label = moved_item.layout_item.label

        # 目标插入位置 = new_label 对应的序号（A=0, B=1, …）
        if isinstance(new_label, str) and len(new_label) == 1 and 'A' <= new_label <= 'Z':
            target_index = ord(new_label) - 65
        else:
            target_index = len(self.rect_items)

        # 其余图按现有标签顺序排好，再把 moved_item 插到目标位置
        remaining = [it for it in self.rect_items if it is not moved_item]
        remaining.sort(key=lambda it: self._label_rank(it.layout_item.label))
        target_index = max(0, min(target_index, len(remaining)))
        new_order = remaining[:target_index] + [moved_item] + remaining[target_index:]

        # 按新顺序重新编号为连续 A、B、C…
        for idx, it in enumerate(new_order):
            lab = chr(65 + idx)
            it.layout_item.label = lab
            it.label_text.setPlainText(lab)

        self._sync_to_canvas()
        self.capture_history_state(f"标签 {old_label} → {new_label}（其余自动顺延）")
        self.statusBar().showMessage(
            f"已将标签改为 {new_label}，其余标签自动顺延保持连续")

    def delete_selected(self):
        """Delete selected items and renumber labels - V15 FIX."""
        selected_items = [item for item in self.rect_items if item.isSelected()]
        if not selected_items:
            return
        # V15 FIX: Use in-place removal to maintain list reference
        for item in selected_items:
            if item in self.rect_items:
                self.scene.removeItem(item)
                self.rect_items.remove(item)
        # V15 FIX: Sync back to canvas
        self._sync_to_canvas()
        self.renumber_labels()
        self.capture_history_state(f"已删除 {len(selected_items)} 个图片")
        self.statusBar().showMessage(f"已删除 {len(selected_items)} 个图片，标签已重新编号")

    def copy_selected_items(self):
        """V16 NEW: Copy selected items to internal clipboard for cross-canvas paste."""
        selected_items = [item for item in self.rect_items if item.isSelected()]
        if not selected_items:
            self.statusBar().showMessage("没有选中的图片")
            return

        # Clear clipboard and copy selected items
        self.internal_clipboard = []
        for item in selected_items:
            # Store layout item state
            state = item.get_current_state()
            self.internal_clipboard.append(state)

        self.statusBar().showMessage(f"已复制 {len(selected_items)} 个图片到剪贴板")

    def paste_items(self):
        """V16 IMPROVED: Smart paste - system clipboard files or internal clipboard items.

        Priority:
        1. If system clipboard has files (PDF/images), paste from system clipboard
        2. Otherwise, paste from internal clipboard (cross-canvas copy)
        """
        # V16: First check if system clipboard has files
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()

            if mime_data.hasUrls():
                # System clipboard has files, use original paste behavior
                self.paste_from_clipboard()
                return
        except Exception as e:
            print(f"Warning: Failed to check system clipboard: {e}")

        # V16: If no system clipboard files, use internal clipboard
        if not self.internal_clipboard:
            self.statusBar().showMessage("剪贴板为空")
            return

        if not self.current_canvas:
            self.statusBar().showMessage("没有活动的画布")
            return

        # Calculate offset for pasted items (10mm right and down)
        offset_x = 10.0
        offset_y = 10.0

        # Add pasted items to current canvas
        pasted_count = 0
        for state in self.internal_clipboard:
            # Create new layout item with offset position
            new_layout = LayoutItem(
                pdf_info=state.pdf_info,
                x=state.x + offset_x,
                y=state.y + offset_y,
                width=state.width,
                height=state.height,
                rotation=state.rotation,
                label=chr(65 + len(self.rect_items))  # Assign next available label
            )

            # Add to current layouts
            self.current_layouts.append(new_layout)

            # Create graphics item
            rect_item = ResizableRectItem(new_layout, self)
            rect_item.snap_to_grid = self.snap_enabled
            self.scene.addItem(rect_item)
            self.rect_items.append(rect_item)
            pasted_count += 1

        # Sync to canvas
        self._sync_to_canvas()

        # Renumber all labels
        self.renumber_labels()

        # Capture history
        self.capture_history_state(f"已粘贴 {pasted_count} 个图片")
        self.statusBar().showMessage(f"已粘贴 {pasted_count} 个图片到当前画布（来自内部剪贴板）")

    def browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(self, "选择PDF文件夹")
        if folder:
            self.folder_path = folder
            self.load_pdfs()

    def rescan_folder(self):
        """Rescan current folder."""
        if self.folder_path:
            self.load_pdfs()

    def load_pdfs(self):
        """Load PDF files from folder - V15 FIX."""
        try:
            # V15 FIX: Use clear() + extend() to maintain list reference
            new_pdfs = scan_pdf_folder(self.folder_path)
            self.pdf_files.clear()
            self.pdf_files.extend(new_pdfs)
            # V15 FIX: Sync back to canvas
            self._sync_to_canvas()

            self.file_list.clear()

            for pdf in self.pdf_files:
                orientation = "竖图" if pdf.is_tall else "横图" if pdf.is_wide else "方图"
                item_text = f"{pdf.filename}\n  {pdf.width:.0f}x{pdf.height:.0f} pt | {orientation}"
                item = QListWidgetItem(item_text)
                self.file_list.addItem(item)

            self.statusBar().showMessage(f"已加载 {len(self.pdf_files)} 个PDF文件")

            if self.pdf_files:
                # V19: 导入后给出"全局统一缩放换行"的初始铺排（按文件顺序 = 标签 A、B、C…）
                engine = LayoutEngine(
                    self.get_canvas_width(),
                    self.get_canvas_height(),
                    self.get_margin(),
                    self.get_spacing()
                )
                new_layouts = engine.flow_import(self.pdf_files)
                self.current_layouts.clear()
                self.current_layouts.extend(new_layouts)
                self.update_canvas()
                self.update_utilization(engine)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载PDF失败: {e}")

    # ==================================================================
    # V19 排版：智能网格（每行统一系数等比缩放，从左铺满画布宽度）
    # ==================================================================

    @staticmethod
    def _label_rank(label):
        """把标签转成可排序的序号，用于确定"标签顺序"。

        单个大写字母 A、B、C… 直接用其在字母表中的位置；其余情况兜底为字符串。
        """
        if isinstance(label, str) and len(label) == 1 and 'A' <= label <= 'Z':
            return (0, ord(label) - 65)
        return (1, str(label))

    @staticmethod
    def _smart_grid_column_presets(count):
        """Return V19 asymmetric column presets matching selected figure count."""
        presets = {
            3: [("左二右一", "2+1"), ("左一右二", "1+2")],
            4: [("左三右一", "3+1"), ("左一右三", "1+3")],
            5: [("左三右二", "3+2"), ("左二右三", "2+3")],
            6: [("左四右二", "4+2"), ("左二右四", "2+4"), ("三列各二", "2+2+2")],
        }
        return presets.get(count, [])

    def apply_smart_grid_layout(self):
        """V19 智能网格：选中图按 行×列 排列；可选「等高填充」到鼠标画出的宽度。

        - 复选框「等高填充宽度」默认勾选：点 OK 后用鼠标在画布上拖一条横线，
          线长即填充宽度（线不留在图上）。该行/各行的图被缩放到【同一高度】正好铺满该宽度——
          等高的图永远保持等高（修复了之前多行系数不一致的问题）。
        - 取消勾选：等同 V18 原版——仅把图按 行×列 摆好，不改变任何图片大小。
        - 直接单击（不拖动）= 用整幅画布可用宽度填充，省去画线。
        """
        selected = [it for it in self.rect_items if it.isSelected()]
        if len(selected) < 1:
            QMessageBox.information(self, "提示", "请先选中要排列的图片")
            return

        selected.sort(key=lambda it: self._label_rank(it.layout_item.label))
        count = len(selected)

        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QRadioButton,
                                     QDialogButtonBox, QLabel, QButtonGroup,
                                     QCheckBox, QLineEdit)
        dialog = QDialog(self)
        dialog.setWindowTitle("智能网格排列")
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"已选中 {count} 个图片，请选择排列方式："))

        radio_buttons = []
        custom_radio = None
        custom_input = None
        if count == 1:
            selected_rows = selected_cols = 1   # 单图无需行列选择
        else:
            arrangements = []
            for rows in range(1, count + 1):
                cols = math.ceil(count / rows)
                if (rows - 1) * cols >= count:
                    continue
                arrangements.append((rows, cols))
            arrangements = sorted(set(arrangements),
                                  key=lambda rc: (abs(rc[0] - rc[1]), rc[0]))
            button_group = QButtonGroup(dialog)
            for i, (rows, cols) in enumerate(arrangements):
                radio = QRadioButton(f"{rows} 行 × {cols} 列")
                if i == 0:
                    radio.setChecked(True)
                radio_buttons.append({
                    "radio": radio,
                    "mode": "grid",
                    "rows": rows,
                    "cols": cols,
                    "pattern": None,
                })
                button_group.addButton(radio)
                layout.addWidget(radio)

            column_presets = self._smart_grid_column_presets(count)
            if column_presets:
                layout.addWidget(QLabel("非对称模板："))
                for title, pattern in column_presets:
                    radio = QRadioButton(f"{title}（{pattern}）")
                    radio_buttons.append({
                        "radio": radio,
                        "mode": "columns",
                        "rows": None,
                        "cols": None,
                        "pattern": pattern,
                    })
                    button_group.addButton(radio)
                    layout.addWidget(radio)

            custom_radio = QRadioButton("自定义列模板")
            custom_input = QLineEdit()
            custom_input.setPlaceholderText("例如 2+1、3+1、1+2、2+2+2")
            radio_buttons.append({
                "radio": custom_radio,
                "mode": "columns",
                "rows": None,
                "cols": None,
                "pattern": "custom",
            })
            button_group.addButton(custom_radio)
            layout.addWidget(custom_radio)
            layout.addWidget(custom_input)

        chk_fill = QCheckBox("等高填充宽度（点 OK 后用鼠标拖一条横线指定宽度；单击=整幅画布宽度）")
        chk_fill.setChecked(True)
        layout.addWidget(chk_fill)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        if count > 1:
            selected_rows = selected_cols = selected_pattern = selected_mode = None
            for option in radio_buttons:
                if option["radio"].isChecked():
                    selected_mode = option["mode"]
                    selected_rows = option["rows"]
                    selected_cols = option["cols"]
                    selected_pattern = option["pattern"]
                    break
            if selected_mode is None:
                return
            if selected_pattern == "custom":
                selected_pattern = custom_input.text().strip()
            if selected_mode == "columns":
                try:
                    selected_column_counts = LayoutEngine.parse_column_pattern(selected_pattern, count)
                except ValueError as e:
                    QMessageBox.warning(self, "模板错误", str(e))
                    return
            else:
                selected_column_counts = None
        else:
            selected_mode = "grid"
            selected_pattern = None
            selected_column_counts = None

        do_fill = chk_fill.isChecked()

        if not do_fill:
            if selected_column_counts:
                QMessageBox.information(self, "提示", "非对称模板需要勾选“等高填充宽度”。")
                return
            # V18 原版行为：仅按行列摆放，不缩放
            self.arrange_items_in_grid(selected, selected_rows, selected_cols)
            return

        # 等高填充：进入画线模式，拿到宽度后再排版
        self._pending_grid = {
            'items': selected,
            'rows': selected_rows,
            'cols': selected_cols,
            'count': count,
            'mode': selected_mode,
            'pattern': selected_pattern,
            'column_counts': selected_column_counts,
        }
        self.view.start_fill_line(self._on_fill_line_drawn)
        self.statusBar().showMessage(
            "请在画布上拖出一条横线指定填充宽度（直接单击=用整幅画布宽度；右键取消）", 0)

    def arrange_items_in_grid(self, items, rows, cols):
        """V18 原版智能网格：把图按 行×列 摆成网格，单元格按最大图尺寸对齐，不改变图片大小。"""
        if not items:
            return
        spacing = self.get_spacing()
        max_w = max(it.layout_item.width for it in items)
        max_h = max(it.layout_item.height for it in items)
        total_w = cols * max_w + (cols - 1) * spacing
        total_h = rows * max_h + (rows - 1) * spacing
        start_x = max(self.get_margin(), (self.get_canvas_width() - total_w) / 2)
        start_y = max(self.get_margin(), (self.get_canvas_height() - total_h) / 2)
        for idx, it in enumerate(items):
            r, c = idx // cols, idx % cols
            li = it.layout_item
            li.x = start_x + c * (max_w + spacing)
            li.y = start_y + r * (max_h + spacing)
            it.update_from_layout_item()
        self._sync_to_canvas()
        self.capture_history_state(f"智能网格 {rows}×{cols}（{len(items)} 张，不缩放）")
        self.statusBar().showMessage(
            f"✓ 已按 {rows} 行 × {cols} 列摆放（未缩放）", 5000)

    def _on_fill_line_drawn(self, x_left, x_right, y):
        """画线完成回调：用线宽对选中图做等高填充（单击则退化为整幅画布宽度）。"""
        pending = getattr(self, '_pending_grid', None)
        if not pending:
            return
        self._pending_grid = None

        items = pending['items']
        rows, cols, count = pending['rows'], pending['cols'], pending['count']
        column_counts = pending.get('column_counts')
        pattern = pending.get('pattern')
        margin = self.get_margin()
        gap = self.get_spacing()

        # 线太短（接近单击）→ 用整幅画布可用宽度，从左边距开始
        drawn_w = x_right - x_left
        if drawn_w < 10.0:
            span_left = margin
            span_width = self.get_active_canvas_width() - 2 * margin
            top_y = max(margin, y)
        else:
            span_left = x_left
            span_width = drawn_w
            top_y = y

        engine = LayoutEngine(
            self.get_active_canvas_width(), self.get_active_canvas_height(), margin, gap)

        if column_counts:
            source_items = [it.layout_item for it in items]
            new_layouts = engine.asymmetric_columns(
                source_items,
                column_counts,
                span_left=span_left,
                top_y=top_y,
                span_width=span_width,
                gap=gap,
            )
            for it, new_layout in zip(items, new_layouts):
                li = it.layout_item
                li.x = new_layout.x
                li.y = new_layout.y
                li.width = new_layout.width
                li.height = new_layout.height
                it.update_from_layout_item()
        else:
            cur_y = top_y
            for r in range(rows):
                row_items = items[r * cols:(r + 1) * cols]
                if not row_items:
                    break
                sizes = [(it.layout_item.width, it.layout_item.height) for it in row_items]
                new_sizes = engine.justified_row(sizes, span_width, gap)
                x = span_left
                row_h = 0.0
                for it, (w, h) in zip(row_items, new_sizes):
                    li = it.layout_item
                    li.x, li.y, li.width, li.height = x, cur_y, w, h
                    it.update_from_layout_item()
                    x += w + gap
                    row_h = max(row_h, h)
                cur_y += row_h + gap

        self._sync_to_canvas()
        layout_name = f"列模板 {pattern}" if column_counts else f"{rows}×{cols}"
        self.capture_history_state(f"智能网格等高填充 {layout_name}（{count} 张）")
        self.update_utilization(engine)
        self.statusBar().showMessage(
            f"✓ 已按 {layout_name} 把 {count} 张图填充到宽度 {span_width:.0f} mm", 5000)

    def update_utilization(self, engine):
        """Update space utilization label."""
        util = engine.calculate_space_utilization(self.current_layouts)
        self.utilization_label.setText(f"空间利用率: {util:.1f}%")

    def _clone_layout(self, layout: LayoutItem) -> LayoutItem:
        """Create a shallow copy of a layout item."""
        return LayoutItem(
            pdf_info=layout.pdf_info,
            x=layout.x,
            y=layout.y,
            width=layout.width,
            height=layout.height,
            rotation=layout.rotation,
            label=layout.label
        )

    def _apply_label_style(self, rect_item: ResizableRectItem):
        """Apply global label style to a rect item."""
        fontsize = self.get_label_fontsize()
        color = self.get_label_color()
        visible = self.is_label_visible()
        bold = self.is_label_bold()

        font_weight = QFont.Bold if bold else QFont.Normal
        font = QFont("Arial", fontsize, font_weight)
        rect_item.label_text.setFont(font)
        rect_item.label_text.setDefaultTextColor(color)
        rect_item.label_text.setVisible(visible)

    def _load_layouts(self, layouts, reset_history=False):
        """Load layouts onto scene, optionally resetting history."""
        self.history_blocked = True
        try:
            self.scene.clear()
            # V10 FIX: Use clear() instead of reassignment to maintain reference
            self.rect_items.clear()

            # V12: Canvas background with current theme
            canvas_rect = QGraphicsRectItem(0, 0, self.get_canvas_width(), self.get_canvas_height())
            canvas_rect.setPen(QPen(QColor(self.current_theme_class.BORDER_LIGHT), 2, Qt.DashLine))
            canvas_rect.setBrush(QBrush(QColor(self.current_theme_class.CANVAS_BG)))
            canvas_rect.setZValue(-1000)
            canvas_rect.is_canvas_rect = True
            self.scene.addItem(canvas_rect)

            for layout in layouts:
                rect_item = ResizableRectItem(self._clone_layout(layout), self)
                self._apply_label_style(rect_item)
                self.scene.addItem(rect_item)
                self.rect_items.append(rect_item)
        finally:
            self.history_blocked = False

        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

        # V10 FIX: Update current_layouts correctly
        new_layouts = [item.get_current_state() for item in self.rect_items]
        self.current_layouts.clear()
        self.current_layouts.extend(new_layouts)

        if reset_history:
            self.history.reset(self.snapshot_state())

        self.update_history_actions()

        # V8: Update ruler if enabled
        if self.show_ruler:
            self.update_ruler_display()

    def update_canvas(self):
        """Update canvas with current layouts."""
        self._load_layouts(self.current_layouts, reset_history=True)

    def snapshot_state(self):
        """Capture current layout snapshot."""
        return [item.get_current_state() for item in self.rect_items]

    def capture_history_state(self, status_message=None):
        """Capture a snapshot into history and update UI."""
        if self.history_blocked:
            return
        snapshot = self.snapshot_state()
        # V10 FIX: Update current_layouts correctly to maintain reference
        new_layouts = [self._clone_layout(layout) for layout in snapshot]
        self.current_layouts.clear()
        self.current_layouts.extend(new_layouts)
        self.history.capture(snapshot)
        self.update_history_actions()
        if status_message:
            self.statusBar().showMessage(f"{status_message} | Ctrl+Z可撤销")

    def undo_last_action(self):
        """Undo to previous snapshot."""
        snapshot = self.history.undo_state()
        if snapshot is None:
            return
        self._load_layouts(snapshot, reset_history=False)
        self.statusBar().showMessage("已撤销上一步 | Ctrl+Y可重做")

    def redo_last_action(self):
        """Redo to next snapshot."""
        snapshot = self.history.redo_state()
        if snapshot is None:
            return
        self._load_layouts(snapshot, reset_history=False)
        self.statusBar().showMessage("已重做 | Ctrl+Z可撤销")

    def update_history_actions(self):
        """Enable/disable undo & redo buttons based on history."""
        if hasattr(self, 'act_undo'):
            self.act_undo.setEnabled(self.history.can_undo())
        if hasattr(self, 'act_redo'):
            self.act_redo.setEnabled(self.history.can_redo())

    def batch_scale_selected(self, scale_factor: float):
        """Scale all selected items by a factor."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if not selected_items:
            QMessageBox.information(self, "提示", "请先选中要缩放的图片\n(点击图片选中，Ctrl+点击多选，或拖拽框选)")
            return

        changed = False
        for item in selected_items:
            old_rect = item.rect()
            new_width = old_rect.width() * scale_factor
            new_height = old_rect.height() * scale_factor

            aspect_ratio = item.layout_item.pdf_info.aspect_ratio
            new_height = new_width / aspect_ratio

            new_rect = QRectF(0, 0, new_width, new_height)
            if old_rect != new_rect:
                item.setRect(new_rect)
                item.update_label_position()
                changed = True

        if changed:
            scale_pct = int((scale_factor - 1) * 100)
            self.capture_history_state(f"缩放 {scale_pct:+d}%")
            self.statusBar().showMessage(f"已缩放 {len(selected_items)} 个图片")

    def align_selected_left(self):
        """Align all selected items to the left."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        min_x = min(item.pos().x() for item in selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_pos = QPointF(min_x, item.pos().y())
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已左对齐")
            self.statusBar().showMessage(f"已左对齐 {len(selected_items)} 个图片")

    def align_selected_top(self):
        """Align all selected items to the top."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        min_y = min(item.pos().y() for item in selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_pos = QPointF(item.pos().x(), min_y)
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已顶对齐")
            self.statusBar().showMessage(f"已顶对齐 {len(selected_items)} 个图片")

    def align_selected_right(self):
        """Align all selected items to the right."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        max_x = max(item.pos().x() + item.rect().width() for item in selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_x = max_x - item.rect().width()
            new_pos = QPointF(new_x, item.pos().y())
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已右对齐")
            self.statusBar().showMessage(f"已右对齐 {len(selected_items)} 个图片")

    def align_selected_bottom(self):
        """Align all selected items to the bottom."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        max_y = max(item.pos().y() + item.rect().height() for item in selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_y = max_y - item.rect().height()
            new_pos = QPointF(item.pos().x(), new_y)
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已底对齐")
            self.statusBar().showMessage(f"已底对齐 {len(selected_items)} 个图片")

    def align_selected_horizontal_center(self):
        """Align all selected items to horizontal center."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        center_x = sum(item.pos().x() + item.rect().width() / 2 for item in selected_items) / len(selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_x = center_x - item.rect().width() / 2
            new_pos = QPointF(new_x, item.pos().y())
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已水平居中")
            self.statusBar().showMessage(f"已水平居中对齐 {len(selected_items)} 个图片")

    def align_selected_vertical_center(self):
        """Align all selected items to vertical center."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 2:
            QMessageBox.information(self, "提示", "请选中至少2个图片进行对齐")
            return

        center_y = sum(item.pos().y() + item.rect().height() / 2 for item in selected_items) / len(selected_items)

        changed = False
        for item in selected_items:
            old_pos = item.pos()
            new_y = center_y - item.rect().height() / 2
            new_pos = QPointF(item.pos().x(), new_y)
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已垂直居中")
            self.statusBar().showMessage(f"已垂直居中对齐 {len(selected_items)} 个图片")

    def distribute_selected_horizontal(self):
        """Distribute selected items evenly horizontally."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 3:
            QMessageBox.information(self, "提示", "请选中至少3个图片进行均分")
            return

        selected_items.sort(key=lambda item: item.pos().x())

        first_x = selected_items[0].pos().x()
        last_x = selected_items[-1].pos().x()
        total_spacing = last_x - first_x
        spacing = total_spacing / (len(selected_items) - 1)

        changed = False
        for i, item in enumerate(selected_items):
            old_pos = item.pos()
            new_x = first_x + i * spacing
            new_pos = QPointF(new_x, item.pos().y())
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已水平均分")
            self.statusBar().showMessage(f"已水平均分 {len(selected_items)} 个图片")

    def distribute_selected_vertical(self):
        """Distribute selected items evenly vertically."""
        selected_items = [item for item in self.rect_items if item.isSelected()]

        if len(selected_items) < 3:
            QMessageBox.information(self, "提示", "请选中至少3个图片进行均分")
            return

        selected_items.sort(key=lambda item: item.pos().y())

        first_y = selected_items[0].pos().y()
        last_y = selected_items[-1].pos().y()
        total_spacing = last_y - first_y
        spacing = total_spacing / (len(selected_items) - 1)

        changed = False
        for i, item in enumerate(selected_items):
            old_pos = item.pos()
            new_y = first_y + i * spacing
            new_pos = QPointF(item.pos().x(), new_y)
            if old_pos != new_pos:
                item.setPos(new_pos)
                changed = True

        if changed:
            self.capture_history_state("已垂直均分")
            self.statusBar().showMessage(f"已垂直均分 {len(selected_items)} 个图片")

    def generate_preview(self):
        """Generate low-resolution preview."""
        if not self.current_layouts:
            QMessageBox.warning(self, "警告", "请先加载PDF并应用布局")
            return

        current_states = [item.get_current_state() for item in self.rect_items]

        # V10 NEW: Use remembered export directory
        default_dir = self.get_default_export_dir()
        default_path = os.path.join(default_dir, "preview.pdf")

        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存预览PDF", default_path, "PDF Files (*.pdf)"
        )

        if not output_path:
            return

        # V10 NEW: Remember the export directory
        self.update_last_export_dir(output_path)

        try:
            from pdf_output import create_preview_pdf

            self.statusBar().showMessage("正在生成预览...")
            QApplication.processEvents()

            create_preview_pdf(
                current_states,
                self.get_canvas_width(),
                self.get_canvas_height(),
                output_path
            )

            QMessageBox.information(self, "成功", f"预览PDF已生成: {output_path}\n(低分辨率，用于快速检查布局)")
            self.statusBar().showMessage(f"预览已保存: {output_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成预览失败: {e}")
            self.statusBar().showMessage("生成预览失败")

    def get_default_filename(self):
        """Get default filename from folder name."""
        if self.folder_path:
            folder_name = os.path.basename(self.folder_path.rstrip(os.sep))
            return folder_name if folder_name else "Figure"
        return "Figure"

    def get_default_export_dir(self):
        """V10 NEW: Get default export directory (last used, or desktop as fallback)."""
        # First try last export directory
        if self.last_export_dir and os.path.exists(self.last_export_dir):
            return self.last_export_dir

        # Fall back to desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop_path):
            return desktop_path

        # Fall back to home directory
        return os.path.expanduser("~")

    def update_last_export_dir(self, filepath):
        """V10 NEW: Update last export directory from a full file path."""
        if filepath:
            self.last_export_dir = os.path.dirname(filepath)

    def export_with_options(self):
        """Export with format selection and progress bar."""
        if not self.current_layouts:
            QMessageBox.warning(self, "警告", "请先加载PDF并应用布局")
            return

        current_states = [item.get_current_state() for item in self.rect_items]

        format_text = self.export_format.currentText()
        if format_text == 'PDF矢量':
            ext = 'pdf'
            filter_str = "PDF Files (*.pdf)"
        elif format_text == 'TIF图片':
            ext = 'tif'
            filter_str = "TIF Files (*.tif)"
        else:  # PNG图片 (default)
            ext = 'png'
            filter_str = "PNG Files (*.png)"

        # V10 NEW: Use remembered export directory
        default_dir = self.get_default_export_dir()
        default_filename = f"{self.get_default_filename()}.{ext}"
        default_path = os.path.join(default_dir, default_filename)

        output_path, _ = QFileDialog.getSaveFileName(
            self, f"保存{format_text}", default_path, filter_str
        )

        if not output_path:
            return

        # V16 NEW: Check if info file will be overwritten
        base_path = os.path.splitext(output_path)[0]
        info_file = f"{base_path}_info.md"
        if not self._check_file_overwrite(info_file):
            return

        # V10 NEW: Remember the export directory
        self.update_last_export_dir(output_path)

        # V8修复：避免进度框显示数字乱码
        progress = QProgressDialog(f"正在导出{format_text}...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        # V8修复：隐藏进度条中的百分比数字（PyQt5兼容方式）
        from PyQt5.QtWidgets import QProgressBar
        progress_bar = progress.findChild(QProgressBar)
        if progress_bar:
            progress_bar.setTextVisible(False)  # 只显示进度条，不显示百分比
        progress.setLabelText(f"正在导出{format_text}，请稍候...")
        progress.setValue(0)

        self.export_thread = ExportThread(
            current_states,
            self.get_canvas_width(),
            self.get_canvas_height(),
            output_path,
            ext,
            self.get_dpi(),
            self.is_label_bold(),
            self.is_auto_crop(),
            self.get_label_offset()
        )

        self.export_thread.progress.connect(progress.setValue)
        # V16: Pass current_states to callback for figure info export
        self.export_thread.finished_signal.connect(lambda path: self.on_export_finished(path, progress, current_states))
        self.export_thread.error_signal.connect(lambda err: self.on_export_error(err, progress))

        self.export_thread.start()

    def on_export_finished(self, path, progress, current_states=None):
        """Handle export finished - V16: Added figure info export."""
        progress.close()
        crop_msg = " (已自动裁剪空白区域)" if self.is_auto_crop() else ""

        # V16 NEW: Export figure information if exporting from export_with_options
        info_msg = ""
        if current_states:
            base_path = os.path.splitext(path)[0]
            md_path = self._export_figure_info(base_path, current_states)
            if md_path:
                info_msg = f"\n\n图片信息已保存: {md_path}"

        QMessageBox.information(self, "成功", f"文件已导出: {path}{crop_msg}{info_msg}")
        self.statusBar().showMessage(f"已导出: {path}")

    def on_export_error(self, error, progress):
        """Handle export error."""
        progress.close()
        QMessageBox.critical(self, "错误", f"导出失败: {error}")
        self.statusBar().showMessage("导出失败")

    def export_all_formats(self):
        """Export all three formats (PDF, TIF, PNG) at once."""
        if not self.current_layouts:
            QMessageBox.warning(self, "警告", "请先加载PDF并应用布局")
            return

        current_states = [item.get_current_state() for item in self.rect_items]

        # V10 NEW: Use remembered export directory
        default_dir = self.get_default_export_dir()
        default_filename = self.get_default_filename()
        default_path = os.path.join(default_dir, default_filename)

        output_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出位置和文件名（将自动添加扩展名）",
            default_path,
            "All Files (*)"
        )

        if not output_path:
            return

        # V10 NEW: Remember the export directory
        self.update_last_export_dir(output_path)

        base_path = os.path.splitext(output_path)[0]

        # V16 NEW: Check if any output files will be overwritten
        # V17: project sidecar is now .figbox (self-contained container)
        all_output_files = [
            f"{base_path}.pdf",
            f"{base_path}.tif",
            f"{base_path}.png",
            f"{base_path}.figbox",
            f"{base_path}_info.md"
        ]
        if not self._check_file_overwrite(all_output_files):
            return

        # V8修复：避免进度框显示数字乱码
        progress = QProgressDialog("正在导出所有格式，请稍候...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        # V8修复：隐藏进度条中的百分比数字（PyQt5兼容方式）
        from PyQt5.QtWidgets import QProgressBar
        progress_bar = progress.findChild(QProgressBar)
        if progress_bar:
            progress_bar.setTextVisible(False)  # 只显示进度条，不显示百分比
        progress.setValue(0)

        try:
            from pdf_output import export_combined_pdf, export_combined_image

            if self.is_auto_crop() and current_states:
                crop_width, crop_height = self._calculate_crop_dimensions(current_states)
            else:
                crop_width, crop_height = self.get_canvas_width(), self.get_canvas_height()

            progress.setLabelText("正在导出PDF...")
            progress.setValue(10)
            QApplication.processEvents()
            pdf_path = f"{base_path}.pdf"
            export_combined_pdf(current_states, crop_width,
                              crop_height, pdf_path, self.get_dpi(), self.is_label_bold(), self.get_label_offset())

            progress.setLabelText("正在导出TIF...")
            progress.setValue(40)
            QApplication.processEvents()
            tif_path = f"{base_path}.tif"
            export_combined_image(current_states, crop_width,
                                crop_height, tif_path, 'tif', self.get_dpi(), self.is_label_bold(), self.get_label_offset())

            progress.setLabelText("正在导出PNG...")
            progress.setValue(70)
            QApplication.processEvents()
            png_path = f"{base_path}.png"
            export_combined_image(current_states, crop_width,
                                crop_height, png_path, 'png', self.get_dpi(), self.is_label_bold(), self.get_label_offset())

            # V13 NEW: Also save project file with same name
            # V17: Sidecar is now .figbox (self-contained, survives image moves)
            progress.setLabelText("正在保存项目文件...")
            progress.setValue(90)
            QApplication.processEvents()
            figproj_path = f"{base_path}.figbox"
            self._save_project_to_file(figproj_path, current_states)

            # V16 NEW: Export figure information
            progress.setLabelText("正在生成图片信息文件...")
            progress.setValue(95)
            QApplication.processEvents()
            md_path = self._export_figure_info(base_path, current_states)

            progress.setValue(100)
            progress.close()

            crop_msg = "\n(已自动裁剪空白区域)" if self.is_auto_crop() else ""
            info_msg = f"\n图片信息: {md_path}" if md_path else ""
            QMessageBox.information(self, "成功",
                f"已成功导出所有格式:{crop_msg}\n\n"
                f"PDF: {pdf_path}\n"
                f"TIF: {tif_path}\n"
                f"PNG: {png_path}\n"
                f"项目: {figproj_path}"
                f"{info_msg}")
            self.statusBar().showMessage(f"已导出所有格式到: {base_path}")

        except Exception as e:
            progress.close()
            # V8修复：添加详细错误信息便于调试
            import traceback
            error_detail = traceback.format_exc()
            QMessageBox.critical(self, "错误", f"导出失败: {e}\n\n详细错误:\n{error_detail}")
            self.statusBar().showMessage("导出失败")

    def _export_figure_info(self, base_path, current_states):
        """V16 NEW: Export figure information to Markdown file.

        Records the mapping between exported figure labels and original PDF filenames.
        Format: Figure [canvas_name][label] [original_filename]
        Example: Figure 1A 01_富集分析.pdf

        Args:
            base_path: Base path for export (without extension)
            current_states: List of layout items with current state

        Returns:
            md_path: Path to generated Markdown file, or None if failed
        """
        try:
            # Get canvas name from filename (e.g., "Figure 1" from "/path/Figure 1")
            canvas_name = os.path.basename(base_path)

            # Generate Markdown content
            md_lines = []
            md_lines.append(f"# {canvas_name} - 图片信息")
            md_lines.append("")
            md_lines.append(f"**导出时间:** {self._get_current_datetime()}")
            md_lines.append("")
            md_lines.append("## 图片列表")
            md_lines.append("")

            for state in current_states:
                pdf_info = state.pdf_info
                original_filename = pdf_info.filename
                original_path = getattr(pdf_info, "original_path", None)
                path_label = "原始路径"
                if not original_path:
                    original_path = pdf_info.filepath
                    path_label = "当前路径"
                label = state.label
                md_lines.append(f"- **{canvas_name}{label}**")
                md_lines.append(f"  - 文件名: `{original_filename}`")
                md_lines.append(f"  - {path_label}: `{original_path}`")

            # Save as markdown file
            md_path = f"{base_path}_info.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))

            print(f"✓ 图片信息已导出: {md_path}")
            return md_path

        except Exception as e:
            print(f"✗ 导出图片信息失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "警告", f"导出图片信息失败: {e}")
            return None

    def _get_current_datetime(self):
        """V16 NEW: Get current date and time as formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _check_file_overwrite(self, file_paths):
        """V16 NEW: Check if files exist and ask user for confirmation.

        Args:
            file_paths: List of file paths or single file path to check

        Returns:
            True if user confirms overwrite or files don't exist, False otherwise
        """
        # Convert single path to list
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        # Find existing files
        existing_files = [path for path in file_paths if os.path.exists(path)]

        if not existing_files:
            return True  # No files exist, proceed

        # Ask user for confirmation
        file_list = "\n".join([os.path.basename(f) for f in existing_files])
        reply = QMessageBox.question(
            self,
            "文件已存在",
            f"以下文件已存在，是否覆盖？\n\n{file_list}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def _calculate_crop_dimensions(self, layouts):
        """Calculate the canvas size needed to fit all figures - V15 FIX."""
        if not layouts:
            return self.get_canvas_width(), self.get_canvas_height()

        max_right = 0
        max_bottom = 0

        for layout in layouts:
            right = layout.x + layout.width
            bottom = layout.y + layout.height
            max_right = max(max_right, right)
            max_bottom = max(max_bottom, bottom)

        margin = 2
        # V15 FIX: Use max() to ensure all figures fit within the crop area
        # Previously used min() which would crop figures extending beyond canvas
        crop_width = max(1, max_right + margin)  # At least include all figures
        crop_height = max(1, max_bottom + margin)

        return crop_width, crop_height

    def open_export_folder(self):
        """V11 NEW: Open the last export/save folder in file explorer."""
        folder_path = self.get_default_export_dir()

        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "警告", f"文件夹不存在: {folder_path}")
            return

        try:
            import platform
            import subprocess

            system = platform.system()

            if system == "Windows":
                # Windows: use explorer
                os.startfile(folder_path)
            elif system == "Darwin":
                # macOS: use open command
                subprocess.run(["open", folder_path])
            else:
                # Linux: try xdg-open
                subprocess.run(["xdg-open", folder_path])

            self.statusBar().showMessage(f"已打开文件夹: {folder_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {e}\n\n路径: {folder_path}")

    # ------------------------------------------------------------------
    # V17: Project I/O - .figbox container (with .figproj backwards-compat)
    # ------------------------------------------------------------------

    def _build_project_data(self, current_states=None):
        """V17: Build the in-memory project_data dict for the active canvas.

        This is the single source of truth used by both .figbox packing and
        legacy .figproj writing. pdf_path entries are absolute filesystem
        paths at this stage; pack_figbox rewrites them when packaging.
        """
        if not self.current_canvas:
            raise Exception("没有活动的画布")
        canvas = self.current_canvas
        if current_states is None:
            current_states = [item.get_current_state() for item in self.rect_items]
        if not current_states:
            raise Exception("画布为空，无法保存")

        project_data = {
            "version": "19.0",
            "canvas_name": canvas.canvas_name,
            "canvas_width": canvas.canvas_width,
            "canvas_height": canvas.canvas_height,
            "settings": {
                "margin": self.get_margin(),
                "spacing": self.get_spacing(),
                "grid_size": self.grid_size,
                "label_fontsize": self.get_label_fontsize(),
                "label_visible": self.is_label_visible(),
                "label_bold": self.is_label_bold(),
                "label_color": self.label_color_combo.currentText(),
                "label_offset": self.get_label_offset(),
                "dpi": self.get_dpi(),
                "export_format": self.export_format.currentText(),
                "auto_crop": self.is_auto_crop(),
            },
            "layouts": [],
        }

        for layout in current_states:
            project_data["layouts"].append({
                "pdf_path": layout.pdf_info.filepath,
                "original_path": getattr(layout.pdf_info, "original_path", None) or layout.pdf_info.filepath,
                "x": layout.x,
                "y": layout.y,
                "width": layout.width,
                "height": layout.height,
                "rotation": layout.rotation,
                "label": layout.label,
                "expand_boundary": layout.pdf_info.expand_boundary,
                "expanded_filepath": layout.pdf_info.expanded_filepath,
                "cumulative_margin": layout.pdf_info.cumulative_margin,
            })
        return project_data

    def _save_project_to_file(self, save_path, current_states=None):
        """V13/V17: Persist the active canvas to a project file.

        The output format is decided by the extension:
          - .figbox  -> self-contained ZIP container (default in V17)
          - .figproj -> legacy plain-JSON layout-only file (back-compat)
        """
        project_data = self._build_project_data(current_states)
        ext = os.path.splitext(save_path)[1].lower()

        if ext == ".figbox":
            asset_paths = []
            for layout in project_data.get("layouts", []):
                p = layout.get("pdf_path")
                if p and os.path.exists(p):
                    asset_paths.append(p)
            pio.pack_figbox(save_path, project_data, asset_paths)
            logger.info("Saved figbox: %s (%d assets)", save_path, len(asset_paths))
        elif ext == ".figproj":
            import json
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            logger.info("Saved legacy figproj: %s", save_path)
        else:
            raise Exception(f"不支持的项目文件扩展名: {ext}")

    def save_project(self):
        """V17: Save the current canvas as a .figbox container.

        The dialog defaults to .figbox; .figproj remains available as a
        legacy option for users who specifically need the old plain-JSON
        layout file.
        """
        if not self.current_canvas:
            QMessageBox.warning(self, "警告", "没有活动的画布")
            return

        canvas = self.current_canvas
        current_states = [item.get_current_state() for item in self.rect_items]
        if not current_states:
            QMessageBox.warning(self, "警告", "画布为空，无法保存")
            return

        default_dir = self.get_default_export_dir()
        default_filename = f"{canvas.canvas_name}.figbox"
        default_path = os.path.join(default_dir, default_filename)

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self, "保存项目文件",
            default_path,
            "Figure Box (*.figbox);;Legacy Figure Project (*.figproj)"
        )
        if not save_path:
            return

        # Ensure correct extension based on the chosen filter
        if "*.figproj" in (selected_filter or ""):
            if not save_path.lower().endswith(".figproj"):
                save_path += ".figproj"
        else:
            if not save_path.lower().endswith(".figbox"):
                save_path += ".figbox"

        try:
            self._save_project_to_file(save_path, current_states)
            self.update_last_export_dir(save_path)
            QMessageBox.information(self, "成功", f"项目已保存: {save_path}")
            self.statusBar().showMessage(f"已保存项目: {save_path}")
        except Exception as e:
            logger.exception("save_project failed")
            QMessageBox.critical(self, "错误", f"保存项目失败: {e}")
            self.statusBar().showMessage("保存项目失败")

    def load_project(self):
        """V17: Open a project file (.figbox preferred, .figproj supported)."""
        default_dir = self.get_default_export_dir()
        load_path, _ = QFileDialog.getOpenFileName(
            self, "打开项目文件",
            default_dir,
            "Figure Box (*.figbox);;Legacy Figure Project (*.figproj);;All Project Files (*.figbox *.figproj)"
        )
        if not load_path:
            return
        self.load_project_from_path(load_path)

    def load_project_from_path(self, load_path):
        """V17 NEW: Non-interactive project loader used by both the menu
        action and the run_v17.py double-click entry point.

        Handles both .figbox containers and legacy .figproj files. For
        legacy files, prompts the user once to upgrade in place to .figbox.
        """
        if not load_path or not os.path.isfile(load_path):
            QMessageBox.critical(self, "错误", f"项目文件不存在: {load_path}")
            return

        ext = os.path.splitext(load_path)[1].lower()
        temp_dir = None
        legacy_imported = False

        try:
            if ext == ".figbox":
                project_data, temp_dir = pio.unpack_figbox(load_path)
            elif ext == ".figproj":
                project_data, temp_dir = pio.import_legacy_figproj(load_path)
                legacy_imported = True
            else:
                QMessageBox.warning(self, "警告", f"不支持的项目文件类型: {ext}")
                return
        except Exception as e:
            logger.exception("Failed to load project: %s", load_path)
            QMessageBox.critical(self, "错误", f"加载项目失败: {e}")
            return

        try:
            self._apply_project_data(project_data, source_path=load_path,
                                     temp_dir=temp_dir,
                                     legacy_imported=legacy_imported)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.exception("Apply project failed")
            QMessageBox.critical(self, "错误", f"加载项目失败: {e}\n\n详细错误:\n{error_detail}")
            self.statusBar().showMessage("加载项目失败")
            # Best-effort cleanup of the temp dir we just created
            pio.cleanup_temp_dir(temp_dir)
            return

        # Hand temp dir over for app-lifetime cleanup
        if temp_dir:
            self.active_temp_dirs.append(temp_dir)

        # Offer legacy users a one-click upgrade to the new container
        if legacy_imported:
            self._offer_legacy_upgrade(load_path)

    def _apply_project_data(self, project_data, source_path, temp_dir=None,
                            legacy_imported=False):
        """V17: Build a new canvas from a project_data dict.

        Shared by load_project_from_path and (later) the autosave-recover flow.
        """
        canvas_name = project_data.get("canvas_name", "已加载项目")
        canvas_width = project_data.get("canvas_width", 297)
        canvas_height = project_data.get("canvas_height", 210)
        settings = project_data.get("settings", {})
        layouts_data = project_data.get("layouts", [])

        if not layouts_data:
            QMessageBox.warning(self, "警告", "项目文件中没有布局数据")
            return

        canvas = self.create_new_canvas(canvas_name)
        canvas.canvas_width = canvas_width
        canvas.canvas_height = canvas_height

        if settings:
            margin_text = f"{settings.get('margin', 10)}mm"
            if margin_text in [self.margin_combo.itemText(i) for i in range(self.margin_combo.count())]:
                self.margin_combo.setCurrentText(margin_text)

            spacing_text = f"{settings.get('spacing', 5)}mm"
            if spacing_text in [self.spacing_combo.itemText(i) for i in range(self.spacing_combo.count())]:
                self.spacing_combo.setCurrentText(spacing_text)

            fontsize_text = str(settings.get('label_fontsize', 12))
            if fontsize_text in [self.label_fontsize_combo.itemText(i) for i in range(self.label_fontsize_combo.count())]:
                self.label_fontsize_combo.setCurrentText(fontsize_text)

            self.label_visible_check.setChecked(settings.get('label_visible', True))
            self.label_bold_check.setChecked(settings.get('label_bold', True))

            label_color = settings.get('label_color', '黑色')
            if label_color in [self.label_color_combo.itemText(i) for i in range(self.label_color_combo.count())]:
                self.label_color_combo.setCurrentText(label_color)

            offset_text = f"{settings.get('label_offset', 0.25)}mm"
            if offset_text in [self.label_offset_combo.itemText(i) for i in range(self.label_offset_combo.count())]:
                self.label_offset_combo.setCurrentText(offset_text)

            dpi_text = str(settings.get('dpi', 300))
            if dpi_text in [self.dpi_combo.itemText(i) for i in range(self.dpi_combo.count())]:
                self.dpi_combo.setCurrentText(dpi_text)

            export_format = settings.get('export_format', 'PDF矢量')
            if export_format in [self.export_format.itemText(i) for i in range(self.export_format.count())]:
                self.export_format.setCurrentText(export_format)

            self.auto_crop_check.setChecked(settings.get('auto_crop', True))

        loaded_layouts = []
        pdf_files_loaded = []
        missing_files = []

        from pdf_utils import parse_filename, mm_to_points

        for layout_data in layouts_data:
            pdf_path = layout_data.get("pdf_path")
            filename = os.path.basename(pdf_path) if pdf_path else "unknown.pdf"

            pdf_exists = bool(pdf_path) and os.path.exists(pdf_path)
            width = height = 0
            aspect_ratio = 1.0

            if pdf_exists:
                try:
                    doc = fitz.open(pdf_path)
                    if len(doc) == 0:
                        doc.close()
                        pdf_exists = False
                    else:
                        page = doc[0]
                        rect = page.rect
                        width = rect.width
                        height = rect.height
                        aspect_ratio = width / height if height > 0 else 1.0
                        doc.close()
                except Exception as e:
                    logger.warning("Error opening PDF %s: %s", pdf_path, e)
                    pdf_exists = False

            if not pdf_exists:
                # Only happens for legacy .figproj with missing originals.
                # .figbox containers always carry their assets so this branch
                # should never trigger for them.
                layout_width = layout_data.get("width", 100)
                layout_height = layout_data.get("height", 100)
                width = mm_to_points(layout_width) * 2
                height = mm_to_points(layout_height) * 2
                aspect_ratio = width / height if height > 0 else 1.0
                missing_files.append(filename)

            sort_key = parse_filename(filename)
            pdf_info = PDFInfo(
                filepath=pdf_path,
                filename=filename,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                sort_key=sort_key,
                original_path=layout_data.get("original_path") or pdf_path,
            )
            if not pdf_exists:
                pdf_info.is_missing = True
            pdf_info.expand_boundary = layout_data.get("expand_boundary", False)
            pdf_info.expanded_filepath = layout_data.get("expanded_filepath")
            pdf_info.cumulative_margin = layout_data.get("cumulative_margin", 0)

            layout_item = LayoutItem(
                pdf_info=pdf_info,
                x=layout_data.get("x", 0),
                y=layout_data.get("y", 0),
                width=layout_data.get("width", 100),
                height=layout_data.get("height", 100),
                rotation=layout_data.get("rotation", 0),
                label=layout_data.get("label", "A"),
            )
            loaded_layouts.append(layout_item)
            pdf_files_loaded.append(pdf_info)

        if not loaded_layouts:
            QMessageBox.warning(self, "警告", "没有成功加载任何PDF文件")
            return

        canvas.pdf_files.clear()
        canvas.pdf_files.extend(pdf_files_loaded)
        canvas.current_layouts.clear()
        canvas.current_layouts.extend(loaded_layouts)

        canvas_rect_item = None
        for item in canvas.scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, 'is_canvas_rect'):
                canvas_rect_item = item
                break
        if canvas_rect_item:
            canvas_rect_item.setRect(0, 0, canvas_width, canvas_height)

        self._load_layouts(loaded_layouts, reset_history=True)

        self.file_list.clear()
        for pdf in pdf_files_loaded:
            orientation = "竖图" if pdf.is_tall else "横图" if pdf.is_wide else "方图"
            item_text = f"{pdf.filename}\n  {pdf.width:.0f}x{pdf.height:.0f} pt | {orientation}"
            list_item = QListWidgetItem(item_text)
            self.file_list.addItem(list_item)

        if source_path:
            self.update_last_export_dir(source_path)

        # User-facing summary
        success_msg = f"项目已加载: {canvas_name}\n共 {len(loaded_layouts)} 个图片"
        if missing_files:
            success_msg += f"\n\n警告: 以下 {len(missing_files)} 个PDF文件未找到:\n"
            for i, fname in enumerate(missing_files[:5], 1):
                success_msg += f"  {i}. {fname}\n"
            if len(missing_files) > 5:
                success_msg += f"  ... 还有 {len(missing_files) - 5} 个文件\n"
            if legacy_imported:
                success_msg += "\n建议: 升级为 .figbox 格式后图片将永远不会丢失。"

        if legacy_imported:
            title = "旧项目加载成功" if not missing_files else "旧项目加载成功（部分文件丢失）"
        else:
            title = "项目加载成功"
        QMessageBox.information(self, title, success_msg)

        if missing_files:
            self.statusBar().showMessage(f"已加载: {canvas_name} ({len(missing_files)} 个文件丢失)")
        else:
            self.statusBar().showMessage(f"已加载: {canvas_name}")

    def _offer_legacy_upgrade(self, figproj_path):
        """V17: After importing a legacy .figproj, ask to save as .figbox."""
        reply = QMessageBox.question(
            self,
            "升级为 .figbox 格式",
            "检测到旧的 .figproj 项目文件。\n\n"
            "升级为 .figbox 格式后，所有原图会被打包进项目文件，\n"
            "无论原图被移动、重命名或删除，项目都能完整重新打开。\n\n"
            "是否立即另存为 .figbox？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        suggested = os.path.splitext(figproj_path)[0] + ".figbox"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "另存为 figbox", suggested, "Figure Box (*.figbox)"
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".figbox"):
            save_path += ".figbox"

        try:
            self._save_project_to_file(save_path)
            self.update_last_export_dir(save_path)
            QMessageBox.information(self, "升级成功", f"已保存为: {save_path}")
            self.statusBar().showMessage(f"已升级为 figbox: {save_path}")
        except Exception as e:
            logger.exception("Legacy upgrade failed")
            QMessageBox.critical(self, "错误", f"升级失败: {e}")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = FigureCombinerGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
