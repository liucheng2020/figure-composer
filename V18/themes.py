"""
V12 多主题系统
Multiple Theme System for V12

包含多种主题风格供用户选择
"""

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt


class ThemeBase:
    """主题基类"""

    @staticmethod
    def get_stylesheet():
        """子类必须实现此方法"""
        raise NotImplementedError

    @staticmethod
    def apply_palette(app):
        """子类必须实现此方法"""
        raise NotImplementedError


class DarkTheme(ThemeBase):
    """暗黑主题 - 专业级深色主题"""

    # 主题名称和描述
    NAME = "暗黑主题"
    DESCRIPTION = "专业级深色主题，护眼舒适"

    # ===== 主色系 =====
    BG_DARKEST = "#1e1e1e"
    BG_DARK = "#252526"
    BG_MEDIUM = "#2d2d30"
    BG_LIGHT = "#3e3e42"

    FG_PRIMARY = "#cccccc"
    FG_SECONDARY = "#999999"
    FG_DISABLED = "#656565"

    ACCENT_BLUE = "#0e639c"
    ACCENT_BLUE_HOVER = "#1177bb"
    ACCENT_BLUE_ACTIVE = "#094771"

    ACCENT_CYAN = "#00d4ff"
    ACCENT_ORANGE = "#ff9800"
    ACCENT_GREEN = "#4caf50"
    ACCENT_RED = "#f44336"

    BORDER_DARK = "#1e1e1e"
    BORDER_LIGHT = "#3e3e42"
    DIVIDER = "#2d2d30"

    CANVAS_BG = "#1e1e1e"
    CANVAS_GRID = "#2d2d30"
    CONTENT_BG = "#252526"

    SELECTION_BG = "#264f78"
    SELECTION_BORDER = "#00d4ff"

    @staticmethod
    def get_stylesheet():
        """获取暗黑主题样式表"""
        return f"""
        /* ===== 暗黑主题 ===== */
        QMainWindow {{
            background-color: {DarkTheme.BG_DARKEST};
            color: {DarkTheme.FG_PRIMARY};
        }}

        QWidget {{
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.FG_PRIMARY};
            font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
            font-size: 9pt;
        }}

        QToolBar {{
            background-color: {DarkTheme.BG_DARK};
            border: none;
            spacing: 4px;
            padding: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 6px 12px;
            margin: 2px;
        }}

        QToolButton:hover {{
            background-color: {DarkTheme.BG_LIGHT};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
        }}

        QToolButton:pressed {{
            background-color: {DarkTheme.ACCENT_BLUE_ACTIVE};
            border: 1px solid {DarkTheme.ACCENT_BLUE};
        }}

        QToolButton:checked {{
            background-color: {DarkTheme.ACCENT_BLUE};
            border: 1px solid {DarkTheme.ACCENT_BLUE_HOVER};
        }}

        QMenuBar {{
            background-color: {DarkTheme.BG_DARK};
            color: {DarkTheme.FG_PRIMARY};
            border-bottom: 1px solid {DarkTheme.BORDER_DARK};
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
        }}

        QMenuBar::item:selected {{
            background-color: {DarkTheme.BG_LIGHT};
        }}

        QMenuBar::item:pressed {{
            background-color: {DarkTheme.ACCENT_BLUE};
        }}

        QMenu {{
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
        }}

        QMenu::item {{
            padding: 6px 30px 6px 20px;
        }}

        QMenu::item:selected {{
            background-color: {DarkTheme.ACCENT_BLUE};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {DarkTheme.DIVIDER};
            margin: 4px 0px;
        }}

        QPushButton {{
            background-color: {DarkTheme.ACCENT_BLUE};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {DarkTheme.ACCENT_BLUE_HOVER};
        }}

        QPushButton:pressed {{
            background-color: {DarkTheme.ACCENT_BLUE_ACTIVE};
        }}

        QPushButton:disabled {{
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.FG_DISABLED};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {DarkTheme.BG_DARKEST};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {DarkTheme.SELECTION_BG};
        }}

        QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {DarkTheme.ACCENT_BLUE};
        }}

        QComboBox {{
            background-color: {DarkTheme.BG_DARKEST};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            padding: 6px;
            min-width: 80px;
        }}

        QComboBox:hover {{
            border: 1px solid {DarkTheme.ACCENT_BLUE};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {DarkTheme.FG_SECONDARY};
            margin-right: 6px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.FG_PRIMARY};
            selection-background-color: {DarkTheme.ACCENT_BLUE};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
        }}

        QListWidget {{
            background-color: {DarkTheme.BG_DARKEST};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            outline: none;
        }}

        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {DarkTheme.DIVIDER};
        }}

        QListWidget::item:hover {{
            background-color: {DarkTheme.BG_LIGHT};
        }}

        QListWidget::item:selected {{
            background-color: {DarkTheme.SELECTION_BG};
            color: white;
        }}

        QScrollBar:vertical {{
            background-color: {DarkTheme.BG_DARK};
            width: 12px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {DarkTheme.BG_LIGHT};
            min-height: 30px;
            border-radius: 6px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {DarkTheme.BORDER_LIGHT};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {DarkTheme.BG_DARK};
            height: 12px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {DarkTheme.BG_LIGHT};
            min-width: 30px;
            border-radius: 6px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {DarkTheme.BORDER_LIGHT};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        QTabWidget::pane {{
            background-color: {DarkTheme.BG_MEDIUM};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
        }}

        QTabBar::tab {{
            background-color: {DarkTheme.BG_DARK};
            color: {DarkTheme.FG_SECONDARY};
            border: 1px solid {DarkTheme.BORDER_DARK};
            padding: 8px 16px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.ACCENT_CYAN};
            border-bottom: 2px solid {DarkTheme.ACCENT_CYAN};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {DarkTheme.BG_LIGHT};
        }}

        QGroupBox {{
            background-color: {DarkTheme.BG_MEDIUM};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 6px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: {DarkTheme.BG_MEDIUM};
            color: {DarkTheme.ACCENT_CYAN};
        }}

        QDockWidget {{
            color: {DarkTheme.FG_PRIMARY};
        }}

        QDockWidget::title {{
            background-color: {DarkTheme.BG_DARK};
            padding: 6px;
            border-bottom: 1px solid {DarkTheme.BORDER_DARK};
        }}

        QCheckBox, QRadioButton {{
            color: {DarkTheme.FG_PRIMARY};
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {DarkTheme.BORDER_LIGHT};
            background-color: {DarkTheme.BG_DARKEST};
        }}

        QCheckBox::indicator {{
            border-radius: 3px;
        }}

        QRadioButton::indicator {{
            border-radius: 9px;
        }}

        QCheckBox::indicator:checked {{
            background-color: {DarkTheme.ACCENT_BLUE};
            border-color: {DarkTheme.ACCENT_BLUE};
        }}

        QRadioButton::indicator:checked {{
            background-color: {DarkTheme.ACCENT_BLUE};
            border-color: {DarkTheme.ACCENT_BLUE};
        }}

        QSpinBox, QDoubleSpinBox {{
            background-color: {DarkTheme.BG_DARKEST};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            padding: 4px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {DarkTheme.ACCENT_BLUE};
        }}

        QStatusBar {{
            background-color: {DarkTheme.BG_DARK};
            color: {DarkTheme.FG_SECONDARY};
            border-top: 1px solid {DarkTheme.BORDER_DARK};
        }}

        QToolTip {{
            background-color: {DarkTheme.BG_LIGHT};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            padding: 4px 8px;
        }}

        QProgressBar {{
            background-color: {DarkTheme.BG_DARKEST};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            text-align: center;
            color: {DarkTheme.FG_PRIMARY};
        }}

        QProgressBar::chunk {{
            background-color: {DarkTheme.ACCENT_BLUE};
            border-radius: 3px;
        }}

        QSlider::groove:horizontal {{
            background-color: {DarkTheme.BG_DARKEST};
            height: 4px;
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            background-color: {DarkTheme.ACCENT_BLUE};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {DarkTheme.ACCENT_BLUE_HOVER};
        }}
        """

    @staticmethod
    def apply_palette(app):
        """应用暗黑主题调色板"""
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(DarkTheme.BG_MEDIUM))
        palette.setColor(QPalette.WindowText, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.Base, QColor(DarkTheme.BG_DARKEST))
        palette.setColor(QPalette.AlternateBase, QColor(DarkTheme.BG_DARK))
        palette.setColor(QPalette.Text, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor("#ffffff"))
        palette.setColor(QPalette.Button, QColor(DarkTheme.BG_MEDIUM))
        palette.setColor(QPalette.ButtonText, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.Highlight, QColor(DarkTheme.SELECTION_BG))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.Link, QColor(DarkTheme.ACCENT_CYAN))
        palette.setColor(QPalette.LinkVisited, QColor(DarkTheme.ACCENT_BLUE))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DarkTheme.FG_DISABLED))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DarkTheme.FG_DISABLED))

        app.setPalette(palette)


class LightTheme(ThemeBase):
    """明亮主题 - 清新明快的浅色主题"""

    NAME = "明亮主题"
    DESCRIPTION = "清新明快的浅色主题"

    # ===== 主色系 =====
    BG_LIGHTEST = "#ffffff"
    BG_LIGHT = "#f5f5f5"
    BG_MEDIUM = "#e8e8e8"
    BG_DARK = "#d0d0d0"
    BG_DARKEST = "#f0f0f0"  # Alias for compatibility

    FG_PRIMARY = "#333333"
    FG_SECONDARY = "#666666"
    FG_DISABLED = "#999999"

    ACCENT_BLUE = "#0078d4"
    ACCENT_BLUE_HOVER = "#106ebe"
    ACCENT_BLUE_ACTIVE = "#005a9e"

    ACCENT_CYAN = "#00b7c3"
    ACCENT_ORANGE = "#ff8c00"
    ACCENT_GREEN = "#107c10"
    ACCENT_RED = "#e81123"

    BORDER_DARK = "#c0c0c0"
    BORDER_LIGHT = "#d0d0d0"
    DIVIDER = "#e0e0e0"

    CANVAS_BG = "#ffffff"
    CANVAS_GRID = "#e8e8e8"
    CONTENT_BG = "#f5f5f5"

    SELECTION_BG = "#cce8ff"
    SELECTION_BORDER = "#0078d4"

    @staticmethod
    def get_stylesheet():
        """获取明亮主题样式表"""
        return f"""
        /* ===== 明亮主题 ===== */
        QMainWindow {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
        }}

        QWidget {{
            background-color: {LightTheme.BG_LIGHT};
            color: {LightTheme.FG_PRIMARY};
            font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
            font-size: 9pt;
        }}

        QToolBar {{
            background-color: {LightTheme.BG_LIGHT};
            border: none;
            border-bottom: 1px solid {LightTheme.BORDER_LIGHT};
            spacing: 4px;
            padding: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 6px 12px;
            margin: 2px;
        }}

        QToolButton:hover {{
            background-color: {LightTheme.BG_MEDIUM};
            border: 1px solid {LightTheme.BORDER_LIGHT};
        }}

        QToolButton:pressed {{
            background-color: {LightTheme.ACCENT_BLUE_ACTIVE};
            color: white;
            border: 1px solid {LightTheme.ACCENT_BLUE};
        }}

        QToolButton:checked {{
            background-color: {LightTheme.ACCENT_BLUE};
            color: white;
            border: 1px solid {LightTheme.ACCENT_BLUE_HOVER};
        }}

        QMenuBar {{
            background-color: {LightTheme.BG_LIGHT};
            color: {LightTheme.FG_PRIMARY};
            border-bottom: 1px solid {LightTheme.BORDER_LIGHT};
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
        }}

        QMenuBar::item:selected {{
            background-color: {LightTheme.BG_MEDIUM};
        }}

        QMenuBar::item:pressed {{
            background-color: {LightTheme.ACCENT_BLUE};
            color: white;
        }}

        QMenu {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
        }}

        QMenu::item {{
            padding: 6px 30px 6px 20px;
        }}

        QMenu::item:selected {{
            background-color: {LightTheme.ACCENT_BLUE};
            color: white;
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {LightTheme.DIVIDER};
            margin: 4px 0px;
        }}

        QPushButton {{
            background-color: {LightTheme.ACCENT_BLUE};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {LightTheme.ACCENT_BLUE_HOVER};
        }}

        QPushButton:pressed {{
            background-color: {LightTheme.ACCENT_BLUE_ACTIVE};
        }}

        QPushButton:disabled {{
            background-color: {LightTheme.BG_MEDIUM};
            color: {LightTheme.FG_DISABLED};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {LightTheme.SELECTION_BG};
        }}

        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {LightTheme.ACCENT_BLUE};
        }}

        QComboBox {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            padding: 6px;
            min-width: 80px;
        }}

        QComboBox:hover {{
            border: 2px solid {LightTheme.ACCENT_BLUE};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {LightTheme.FG_SECONDARY};
            margin-right: 6px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            selection-background-color: {LightTheme.ACCENT_BLUE};
            selection-color: white;
            border: 1px solid {LightTheme.BORDER_DARK};
        }}

        QListWidget {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            outline: none;
        }}

        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {LightTheme.DIVIDER};
        }}

        QListWidget::item:hover {{
            background-color: {LightTheme.BG_MEDIUM};
        }}

        QListWidget::item:selected {{
            background-color: {LightTheme.SELECTION_BG};
            color: {LightTheme.FG_PRIMARY};
        }}

        QScrollBar:vertical {{
            background-color: {LightTheme.BG_LIGHT};
            width: 12px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {LightTheme.BG_DARK};
            min-height: 30px;
            border-radius: 6px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {LightTheme.BORDER_DARK};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {LightTheme.BG_LIGHT};
            height: 12px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {LightTheme.BG_DARK};
            min-width: 30px;
            border-radius: 6px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {LightTheme.BORDER_DARK};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        QTabWidget::pane {{
            background-color: {LightTheme.BG_LIGHT};
            border: 1px solid {LightTheme.BORDER_LIGHT};
            border-radius: 4px;
        }}

        QTabBar::tab {{
            background-color: {LightTheme.BG_MEDIUM};
            color: {LightTheme.FG_SECONDARY};
            border: 1px solid {LightTheme.BORDER_LIGHT};
            padding: 8px 16px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {LightTheme.BG_LIGHT};
            color: {LightTheme.ACCENT_BLUE};
            border-bottom: 2px solid {LightTheme.ACCENT_BLUE};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {LightTheme.BG_LIGHT};
        }}

        QGroupBox {{
            background-color: {LightTheme.BG_LIGHT};
            border: 1px solid {LightTheme.BORDER_LIGHT};
            border-radius: 6px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: {LightTheme.BG_LIGHT};
            color: {LightTheme.ACCENT_BLUE};
        }}

        QDockWidget {{
            color: {LightTheme.FG_PRIMARY};
        }}

        QDockWidget::title {{
            background-color: {LightTheme.BG_LIGHT};
            padding: 6px;
            border-bottom: 1px solid {LightTheme.BORDER_LIGHT};
        }}

        QCheckBox, QRadioButton {{
            color: {LightTheme.FG_PRIMARY};
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {LightTheme.BORDER_DARK};
            background-color: {LightTheme.BG_LIGHTEST};
        }}

        QCheckBox::indicator {{
            border-radius: 3px;
        }}

        QRadioButton::indicator {{
            border-radius: 9px;
        }}

        QCheckBox::indicator:checked {{
            background-color: {LightTheme.ACCENT_BLUE};
            border-color: {LightTheme.ACCENT_BLUE};
        }}

        QRadioButton::indicator:checked {{
            background-color: {LightTheme.ACCENT_BLUE};
            border-color: {LightTheme.ACCENT_BLUE};
        }}

        QSpinBox, QDoubleSpinBox {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            padding: 4px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {LightTheme.ACCENT_BLUE};
        }}

        QStatusBar {{
            background-color: {LightTheme.BG_LIGHT};
            color: {LightTheme.FG_SECONDARY};
            border-top: 1px solid {LightTheme.BORDER_LIGHT};
        }}

        QToolTip {{
            background-color: {LightTheme.BG_LIGHTEST};
            color: {LightTheme.FG_PRIMARY};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            padding: 4px 8px;
        }}

        QProgressBar {{
            background-color: {LightTheme.BG_MEDIUM};
            border: 1px solid {LightTheme.BORDER_DARK};
            border-radius: 4px;
            text-align: center;
            color: {LightTheme.FG_PRIMARY};
        }}

        QProgressBar::chunk {{
            background-color: {LightTheme.ACCENT_BLUE};
            border-radius: 3px;
        }}

        QSlider::groove:horizontal {{
            background-color: {LightTheme.BG_MEDIUM};
            height: 4px;
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            background-color: {LightTheme.ACCENT_BLUE};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {LightTheme.ACCENT_BLUE_HOVER};
        }}
        """

    @staticmethod
    def apply_palette(app):
        """应用明亮主题调色板"""
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(LightTheme.BG_LIGHT))
        palette.setColor(QPalette.WindowText, QColor(LightTheme.FG_PRIMARY))
        palette.setColor(QPalette.Base, QColor(LightTheme.BG_LIGHTEST))
        palette.setColor(QPalette.AlternateBase, QColor(LightTheme.BG_MEDIUM))
        palette.setColor(QPalette.Text, QColor(LightTheme.FG_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor("#000000"))
        palette.setColor(QPalette.Button, QColor(LightTheme.BG_LIGHT))
        palette.setColor(QPalette.ButtonText, QColor(LightTheme.FG_PRIMARY))
        palette.setColor(QPalette.Highlight, QColor(LightTheme.SELECTION_BG))
        palette.setColor(QPalette.HighlightedText, QColor(LightTheme.FG_PRIMARY))
        palette.setColor(QPalette.Link, QColor(LightTheme.ACCENT_BLUE))
        palette.setColor(QPalette.LinkVisited, QColor(LightTheme.ACCENT_BLUE_ACTIVE))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(LightTheme.FG_DISABLED))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(LightTheme.FG_DISABLED))

        app.setPalette(palette)


class CuteTheme(ThemeBase):
    """可爱主题 - 粉色系可爱主题"""

    NAME = "可爱主题"
    DESCRIPTION = "粉色系可爱温馨主题"

    # ===== 主色系 =====
    BG_LIGHTEST = "#fff5f7"
    BG_LIGHT = "#ffe4e9"
    BG_MEDIUM = "#ffd4dd"
    BG_DARK = "#ffb3c1"
    BG_DARKEST = "#fff0f2"  # Alias for compatibility

    FG_PRIMARY = "#4a4a4a"
    FG_SECONDARY = "#757575"
    FG_DISABLED = "#a0a0a0"

    ACCENT_PINK = "#ff69b4"
    ACCENT_PINK_HOVER = "#ff85c1"
    ACCENT_PINK_ACTIVE = "#ff4da6"

    ACCENT_PURPLE = "#da70d6"
    ACCENT_ORANGE = "#ffa07a"
    ACCENT_GREEN = "#98d982"
    ACCENT_RED = "#ff6b6b"

    BORDER_DARK = "#ffb3c1"
    BORDER_LIGHT = "#ffd4dd"
    DIVIDER = "#ffe4e9"

    CANVAS_BG = "#ffffff"
    CANVAS_GRID = "#ffe4e9"
    CONTENT_BG = "#fff5f7"

    SELECTION_BG = "#ffe4e9"
    SELECTION_BORDER = "#ff69b4"

    @staticmethod
    def get_stylesheet():
        """获取可爱主题样式表"""
        return f"""
        /* ===== 可爱主题 ===== */
        QMainWindow {{
            background-color: {CuteTheme.BG_LIGHTEST};
            color: {CuteTheme.FG_PRIMARY};
        }}

        QWidget {{
            background-color: {CuteTheme.BG_LIGHT};
            color: {CuteTheme.FG_PRIMARY};
            font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
            font-size: 9pt;
        }}

        QToolBar {{
            background-color: {CuteTheme.BG_LIGHTEST};
            border: none;
            border-bottom: 2px solid {CuteTheme.ACCENT_PINK};
            spacing: 4px;
            padding: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            color: {CuteTheme.FG_PRIMARY};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 6px 12px;
            margin: 2px;
        }}

        QToolButton:hover {{
            background-color: {CuteTheme.BG_MEDIUM};
            border: 1px solid {CuteTheme.ACCENT_PINK};
        }}

        QToolButton:pressed {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
            border: 1px solid {CuteTheme.ACCENT_PINK_ACTIVE};
        }}

        QToolButton:checked {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
            border: 1px solid {CuteTheme.ACCENT_PINK_HOVER};
        }}

        QMenuBar {{
            background-color: {CuteTheme.BG_LIGHTEST};
            color: {CuteTheme.FG_PRIMARY};
            border-bottom: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 6px;
        }}

        QMenuBar::item:selected {{
            background-color: {CuteTheme.BG_MEDIUM};
        }}

        QMenuBar::item:pressed {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
        }}

        QMenu {{
            background-color: {CuteTheme.BG_LIGHTEST};
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.ACCENT_PINK};
            border-radius: 8px;
        }}

        QMenu::item {{
            padding: 8px 30px 8px 20px;
            border-radius: 4px;
            margin: 2px 4px;
        }}

        QMenu::item:selected {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
        }}

        QMenu::separator {{
            height: 2px;
            background-color: {CuteTheme.DIVIDER};
            margin: 6px 8px;
        }}

        QPushButton {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
            border: none;
            border-radius: 12px;
            padding: 8px 16px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background-color: {CuteTheme.ACCENT_PINK_HOVER};
        }}

        QPushButton:pressed {{
            background-color: {CuteTheme.ACCENT_PINK_ACTIVE};
        }}

        QPushButton:disabled {{
            background-color: {CuteTheme.BG_MEDIUM};
            color: {CuteTheme.FG_DISABLED};
        }}

        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: white;
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.BORDER_LIGHT};
            border-radius: 8px;
            padding: 6px;
            selection-background-color: {CuteTheme.SELECTION_BG};
        }}

        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QComboBox {{
            background-color: white;
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.BORDER_LIGHT};
            border-radius: 8px;
            padding: 6px;
            min-width: 80px;
        }}

        QComboBox:hover {{
            border: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 7px solid {CuteTheme.ACCENT_PINK};
            margin-right: 6px;
        }}

        QComboBox QAbstractItemView {{
            background-color: white;
            color: {CuteTheme.FG_PRIMARY};
            selection-background-color: {CuteTheme.ACCENT_PINK};
            selection-color: white;
            border: 2px solid {CuteTheme.ACCENT_PINK};
            border-radius: 8px;
        }}

        QListWidget {{
            background-color: white;
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.BORDER_LIGHT};
            border-radius: 8px;
            outline: none;
        }}

        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {CuteTheme.DIVIDER};
            border-radius: 4px;
        }}

        QListWidget::item:hover {{
            background-color: {CuteTheme.BG_MEDIUM};
        }}

        QListWidget::item:selected {{
            background-color: {CuteTheme.SELECTION_BG};
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QScrollBar:vertical {{
            background-color: {CuteTheme.BG_LIGHT};
            width: 14px;
            border: none;
            border-radius: 7px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {CuteTheme.ACCENT_PINK};
            min-height: 30px;
            border-radius: 7px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {CuteTheme.ACCENT_PINK_HOVER};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {CuteTheme.BG_LIGHT};
            height: 14px;
            border: none;
            border-radius: 7px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {CuteTheme.ACCENT_PINK};
            min-width: 30px;
            border-radius: 7px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {CuteTheme.ACCENT_PINK_HOVER};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        QTabWidget::pane {{
            background-color: {CuteTheme.BG_LIGHT};
            border: 2px solid {CuteTheme.ACCENT_PINK};
            border-radius: 8px;
        }}

        QTabBar::tab {{
            background-color: {CuteTheme.BG_MEDIUM};
            color: {CuteTheme.FG_SECONDARY};
            border: 2px solid {CuteTheme.BORDER_LIGHT};
            padding: 8px 16px;
            margin-right: 4px;
            border-radius: 8px 8px 0 0;
        }}

        QTabBar::tab:selected {{
            background-color: {CuteTheme.BG_LIGHT};
            color: {CuteTheme.ACCENT_PINK};
            border-bottom: 3px solid {CuteTheme.ACCENT_PINK};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {CuteTheme.BG_LIGHT};
        }}

        QGroupBox {{
            background-color: {CuteTheme.BG_LIGHTEST};
            border: 2px solid {CuteTheme.ACCENT_PINK};
            border-radius: 12px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 12px;
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
            border-radius: 8px;
        }}

        QDockWidget {{
            color: {CuteTheme.FG_PRIMARY};
        }}

        QDockWidget::title {{
            background-color: {CuteTheme.BG_LIGHTEST};
            padding: 6px;
            border-bottom: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QCheckBox, QRadioButton {{
            color: {CuteTheme.FG_PRIMARY};
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {CuteTheme.ACCENT_PINK};
            background-color: white;
        }}

        QCheckBox::indicator {{
            border-radius: 5px;
        }}

        QRadioButton::indicator {{
            border-radius: 10px;
        }}

        QCheckBox::indicator:checked {{
            background-color: {CuteTheme.ACCENT_PINK};
            border-color: {CuteTheme.ACCENT_PINK};
        }}

        QRadioButton::indicator:checked {{
            background-color: {CuteTheme.ACCENT_PINK};
            border-color: {CuteTheme.ACCENT_PINK};
        }}

        QSpinBox, QDoubleSpinBox {{
            background-color: white;
            color: {CuteTheme.FG_PRIMARY};
            border: 2px solid {CuteTheme.BORDER_LIGHT};
            border-radius: 8px;
            padding: 4px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QStatusBar {{
            background-color: {CuteTheme.BG_LIGHTEST};
            color: {CuteTheme.FG_SECONDARY};
            border-top: 2px solid {CuteTheme.ACCENT_PINK};
        }}

        QToolTip {{
            background-color: {CuteTheme.ACCENT_PINK};
            color: white;
            border: 2px solid {CuteTheme.ACCENT_PINK_ACTIVE};
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 500;
        }}

        QProgressBar {{
            background-color: {CuteTheme.BG_MEDIUM};
            border: 2px solid {CuteTheme.ACCENT_PINK};
            border-radius: 8px;
            text-align: center;
            color: {CuteTheme.FG_PRIMARY};
        }}

        QProgressBar::chunk {{
            background-color: {CuteTheme.ACCENT_PINK};
            border-radius: 6px;
        }}

        QSlider::groove:horizontal {{
            background-color: {CuteTheme.BG_MEDIUM};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background-color: {CuteTheme.ACCENT_PINK};
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
            border: 2px solid white;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {CuteTheme.ACCENT_PINK_HOVER};
        }}
        """

    @staticmethod
    def apply_palette(app):
        """应用可爱主题调色板"""
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(CuteTheme.BG_LIGHT))
        palette.setColor(QPalette.WindowText, QColor(CuteTheme.FG_PRIMARY))
        palette.setColor(QPalette.Base, QColor(CuteTheme.BG_LIGHTEST))
        palette.setColor(QPalette.AlternateBase, QColor(CuteTheme.BG_MEDIUM))
        palette.setColor(QPalette.Text, QColor(CuteTheme.FG_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor("#000000"))
        palette.setColor(QPalette.Button, QColor(CuteTheme.BG_LIGHT))
        palette.setColor(QPalette.ButtonText, QColor(CuteTheme.FG_PRIMARY))
        palette.setColor(QPalette.Highlight, QColor(CuteTheme.SELECTION_BG))
        palette.setColor(QPalette.HighlightedText, QColor(CuteTheme.FG_PRIMARY))
        palette.setColor(QPalette.Link, QColor(CuteTheme.ACCENT_PINK))
        palette.setColor(QPalette.LinkVisited, QColor(CuteTheme.ACCENT_PURPLE))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(CuteTheme.FG_DISABLED))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(CuteTheme.FG_DISABLED))

        app.setPalette(palette)


# 主题注册表
AVAILABLE_THEMES = {
    "dark": DarkTheme,
    "light": LightTheme,
    "cute": CuteTheme,
}


def get_theme_names():
    """获取所有可用主题的名称列表"""
    return [(key, theme.NAME, theme.DESCRIPTION) for key, theme in AVAILABLE_THEMES.items()]


def apply_theme(app, theme_key="dark"):
    """应用指定的主题

    Args:
        app: QApplication实例
        theme_key: 主题键名 ("dark", "light", "cute")
    """
    if theme_key not in AVAILABLE_THEMES:
        print(f"警告: 主题 '{theme_key}' 不存在，使用默认暗黑主题")
        theme_key = "dark"

    theme_class = AVAILABLE_THEMES[theme_key]
    app.setStyleSheet(theme_class.get_stylesheet())
    theme_class.apply_palette(app)

    return theme_class
