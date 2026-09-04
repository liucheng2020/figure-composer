r"""
学术组图工具 V20 - 启动器 (Agent CLI Edition)

V20 保留 V19 的全部 GUI 能力，并新增独立 Agent CLI。

V19 相对 V18 的变化:
1. 删除 7 个低效自动排版（规则网格/紧凑/黄金分割/瀑布流/智能分组/自适应权重/AI智能布局）
2. 升级「🔳 智能网格」：选中图按任意 行×列 排列；每行乘同一系数等比缩放，
   从画布左边铺满整行宽度（保留各图比例、高度可不同）
3. 拖图落在拖放位置（图中心对准落点），不再自动跳到正中央
4. 标签级联联动：改某图标签为已存在标签时，其余标签自动顺延，始终保持 A、B、C… 连续
5. 导出默认 1000 DPI（出版级）；屏幕预览仍用低 DPI。光栅(PNG/TIF)按目标尺寸直接渲染提速；
   点多的矢量图（如 UMAP）建议导出 PDF（矢量嵌入，最快且无限清晰）
6. 完全兼容 V18 的 .figbox / .figproj 项目文件

使用方式:
    python run_v20.py [theme]                 交互式启动
    python run_v20.py path\to\project.figbox  直接打开项目（双击场景）
    python run_v20.py [theme] path\to\x.figbox  指定主题并打开项目
    python run_v20.py --smoke-test            启动完整 GUI 后自动退出，仅供构建验收

主题: light (默认), dark, cute
"""

import os
import sys


AGENT_CLI_COMMANDS = {
    "compose", "inspect", "relayout", "edit",
    "boundary", "canvas", "export", "preferences",
}


def _is_agent_cli_command(argv):
    """判断当前启动是否应交给 Agent CLI。"""
    return len(argv) > 1 and argv[1].lower() in AGENT_CLI_COMMANDS


def _parse_args(argv):
    """把 sys.argv 解析为 (theme_key, project_path, smoke_test)。"""
    theme_key = "light"
    project_path = None
    smoke_test = False
    valid_themes = {"light", "dark", "cute"}

    for arg in argv[1:]:
        low = arg.lower()
        if low in valid_themes:
            theme_key = low
            continue
        if low == "--smoke-test":
            smoke_test = True
            continue
        if (low.endswith(".figbox") or low.endswith(".figproj")) and os.path.isfile(arg):
            project_path = os.path.abspath(arg)
            continue
        print(f"[run_v20] 忽略未知参数: {arg}")

    return theme_key, project_path, smoke_test


def main():
    if _is_agent_cli_command(sys.argv):
        from agent_cli import main as agent_cli_main
        return agent_cli_main(sys.argv[1:])

    theme_key, project_path, smoke_test = _parse_args(sys.argv)

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    from log_setup import setup_logging
    from gui_editor import FigureCombinerGUI
    from themes import apply_theme, AVAILABLE_THEMES
    from auto_backup import AutoBackupManager

    log_path = setup_logging()
    import logging
    logger = logging.getLogger("run_v20")
    logger.info("FigBox V20 starting; theme=%s, project=%s, log=%s",
                theme_key, project_path, log_path)

    app = QApplication(sys.argv)
    app.setApplicationName("学术组图工具 V20 FigBox")
    app.setOrganizationName("Research Tools")
    app.setStyle("Fusion")

    theme_class = apply_theme(app, theme_key)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    window = FigureCombinerGUI()
    window.current_theme = theme_key
    window.current_theme_class = AVAILABLE_THEMES.get(theme_key, theme_class)

    theme_name = theme_class.NAME
    window.setWindowTitle(f"学术组图工具 V20.0 FigBox - {theme_name}")
    window.show()

    backup_manager = None
    if window.user_settings.get("autosave_enabled", True):
        interval = int(window.user_settings.get("autosave_interval_minutes", 5))
        backup_manager = AutoBackupManager(window, interval_minutes=interval)
        backup_manager.start()
    window._backup_manager = backup_manager

    if project_path:
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: window.load_project_from_path(project_path))

    if smoke_test:
        from PyQt5.QtCore import QTimer
        logger.info("FigBox V20 smoke test initialized successfully")
        QTimer.singleShot(2000, app.quit)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
