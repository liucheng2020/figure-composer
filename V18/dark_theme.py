"""
V12 暗黑主题样式系统
Dark Theme Style System for V12

现代化、专业级的暗黑主题设计
"""

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class DarkTheme:
    """暗黑主题配色和样式定义"""

    # ===== 主色系 =====
    # 背景色
    BG_DARKEST = "#1e1e1e"      # 最深背景（主窗口）
    BG_DARK = "#252526"          # 深色背景（工具栏、侧边栏）
    BG_MEDIUM = "#2d2d30"        # 中等背景（面板）
    BG_LIGHT = "#3e3e42"         # 浅色背景（悬停）

    # 前景色（文字）
    FG_PRIMARY = "#cccccc"       # 主要文字
    FG_SECONDARY = "#999999"     # 次要文字
    FG_DISABLED = "#656565"      # 禁用文字

    # 强调色（品牌色）
    ACCENT_BLUE = "#0e639c"      # 主强调色
    ACCENT_BLUE_HOVER = "#1177bb"  # 悬停
    ACCENT_BLUE_ACTIVE = "#094771"  # 激活

    # 辅助强调色
    ACCENT_CYAN = "#00d4ff"      # 青色（选中、高亮）
    ACCENT_ORANGE = "#ff9800"    # 橙色（警告）
    ACCENT_GREEN = "#4caf50"     # 绿色（成功）
    ACCENT_RED = "#f44336"       # 红色（错误、删除）

    # 边框和分割线
    BORDER_DARK = "#1e1e1e"
    BORDER_LIGHT = "#3e3e42"
    DIVIDER = "#2d2d30"

    # 画布和内容区
    CANVAS_BG = "#1e1e1e"        # 画布背景
    CANVAS_GRID = "#2d2d30"      # 网格线
    CONTENT_BG = "#252526"       # 内容区背景

    # 选中状态
    SELECTION_BG = "#264f78"     # 选中背景
    SELECTION_BORDER = "#00d4ff"  # 选中边框

    @staticmethod
    def get_stylesheet():
        """获取完整的QSS样式表"""
        return f"""
        /* ===== 全局样式 ===== */
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

        /* ===== 工具栏 ===== */
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

        /* ===== 菜单栏 ===== */
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

        /* ===== 按钮 ===== */
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

        /* ===== 输入框 ===== */
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

        /* ===== 下拉框 ===== */
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

        /* ===== 列表 ===== */
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

        /* ===== 滚动条 ===== */
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

        /* ===== 标签页 ===== */
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

        /* ===== 分组框 ===== */
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

        /* ===== Dock窗口 ===== */
        QDockWidget {{
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
            color: {DarkTheme.FG_PRIMARY};
        }}

        QDockWidget::title {{
            background-color: {DarkTheme.BG_DARK};
            padding: 6px;
            border-bottom: 1px solid {DarkTheme.BORDER_DARK};
        }}

        /* ===== 复选框和单选框 ===== */
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

        /* ===== 数值输入框 ===== */
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

        /* ===== 状态栏 ===== */
        QStatusBar {{
            background-color: {DarkTheme.BG_DARK};
            color: {DarkTheme.FG_SECONDARY};
            border-top: 1px solid {DarkTheme.BORDER_DARK};
        }}

        /* ===== 工具提示 ===== */
        QToolTip {{
            background-color: {DarkTheme.BG_LIGHT};
            color: {DarkTheme.FG_PRIMARY};
            border: 1px solid {DarkTheme.BORDER_LIGHT};
            border-radius: 4px;
            padding: 4px 8px;
        }}

        /* ===== 进度条 ===== */
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

        /* ===== 滑块 ===== */
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
        """应用调色板到应用程序"""
        palette = QPalette()

        # 窗口背景
        palette.setColor(QPalette.Window, QColor(DarkTheme.BG_MEDIUM))
        palette.setColor(QPalette.WindowText, QColor(DarkTheme.FG_PRIMARY))

        # 基础背景
        palette.setColor(QPalette.Base, QColor(DarkTheme.BG_DARKEST))
        palette.setColor(QPalette.AlternateBase, QColor(DarkTheme.BG_DARK))

        # 文字
        palette.setColor(QPalette.Text, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor("#ffffff"))

        # 按钮
        palette.setColor(QPalette.Button, QColor(DarkTheme.BG_MEDIUM))
        palette.setColor(QPalette.ButtonText, QColor(DarkTheme.FG_PRIMARY))

        # 高亮
        palette.setColor(QPalette.Highlight, QColor(DarkTheme.SELECTION_BG))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

        # 链接
        palette.setColor(QPalette.Link, QColor(DarkTheme.ACCENT_CYAN))
        palette.setColor(QPalette.LinkVisited, QColor(DarkTheme.ACCENT_BLUE))

        # 禁用状态
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DarkTheme.FG_DISABLED))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DarkTheme.FG_DISABLED))

        app.setPalette(palette)
