#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术组图工具 V20 - EXE 打包脚本 (Agent CLI Edition)

V20 保留 V19 GUI 能力并新增独立 agent_cli.py。

V19 相对 V18 的变化:
1. 删除 7 个低效自动排版，升级「🔳 智能网格」：选中图按 行×列 排列，
   可选「等高填充」——点 OK 后用鼠标拖一条横线指定宽度，选中图等高铺满该宽度
   （等高图保持等高；单击=整幅画布宽度；取消勾选=V17 仅摆放不缩放）
2. 拖图落在拖放位置（图中心对准落点），不再自动跳到正中央
3. 标签级联联动：改某图标签为已存在标签时，其余标签自动顺延，保持 A、B、C… 连续
4. 导出默认 1000 DPI；光栅(PNG/TIF)按目标像素直接渲染提速；点多的矢量图建议导出 PDF
5. 完全兼容 V18 的 .figbox / .figproj 项目文件

打包后会在 dist/ 目录中得到:
  ├── 学术组图工具V20.exe
  ├── register_figbox.bat        注册 .figbox 文件关联（需管理员）
  └── unregister_figbox.bat      取消注册
"""

import os
import sys
import subprocess
import shutil

EXE_NAME = "学术组图工具V20"
ENTRY = "run_v20.py"


def print_header(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70 + "\n")


def check_dependencies():
    print("检查依赖包...")
    print("-" * 70)
    required = {
        "PyQt5": "PyQt5",
        "PyMuPDF": "fitz",
        "Pillow": "PIL",
        "PyInstaller": "PyInstaller",
    }
    missing = []
    for package, import_name in required.items():
        try:
            __import__(import_name)
            print(f"  [OK]   {package}")
        except ImportError:
            print(f"  [MISS] {package}")
            missing.append(package)
    if missing:
        print("\n请先安装以下依赖包:")
        for pkg in missing:
            print(f"  pip install {pkg}")
        return False
    print("\n依赖完整\n")
    return True


def cleanup_old_builds():
    print("移动旧的构建文件到 .Trash...")
    print("-" * 70)
    trash_dir = ".Trash"
    os.makedirs(trash_dir, exist_ok=True)
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    for d in ("build", "dist", "__pycache__"):
        if os.path.exists(d):
            try:
                target = os.path.join(trash_dir, f"{d}_{stamp}")
                shutil.move(d, target)
                print(f"  moved dir  {d} -> {target}")
            except OSError as e:
                print(f"  warning: cannot move {d}: {e}")
    for f in (f"{EXE_NAME}.spec",):
        if os.path.exists(f):
            try:
                target = os.path.join(trash_dir, f"{os.path.basename(f)}_{stamp}")
                shutil.move(f, target)
                print(f"  moved file {f} -> {target}")
            except OSError as e:
                print(f"  warning: cannot move {f}: {e}")
    print()


def build_exe():
    print_header(f"{EXE_NAME} - PyInstaller 打包")

    print("[1/4] 检查依赖")
    if not check_dependencies():
        input("\n按回车退出..."); return False

    print("[2/4] 清理旧构建")
    cleanup_old_builds()

    print("[3/4] 打包 EXE，预计 3-5 分钟，请耐心等待...\n")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--onefile", "--windowed",
        "--name", EXE_NAME,
        # ---- core deps ----
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=fitz",
        "--hidden-import=PIL",
        # ---- V20 own modules ----
        "--hidden-import=themes",
        "--hidden-import=dark_theme",
        "--hidden-import=layout_engine",
        "--hidden-import=pdf_utils",
        "--hidden-import=pdf_output",
        "--hidden-import=pdf_boundary_fix",
        "--hidden-import=canvas_widget",
        "--hidden-import=gui_editor",
        "--hidden-import=project_io",
        "--hidden-import=auto_backup",
        "--hidden-import=log_setup",
        "--hidden-import=settings_manager",
        "--hidden-import=provenance_utils",
        "--hidden-import=project_ops",
        "--hidden-import=agent_cli",
        # ---- excludes for size ----
        "--exclude-module=matplotlib",
        "--exclude-module=tkinter",
        "--exclude-module=scipy",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=pyarrow",
        "--exclude-module=numba",
        "--exclude-module=llvmlite",
        "--exclude-module=sqlalchemy",
        "--exclude-module=openpyxl",
        "--exclude-module=pytest",
        "--exclude-module=pygments",
        "--exclude-module=jinja2",
    ]
    if os.path.exists("icon.ico"):
        cmd.extend(["--icon", "icon.ico"])
    cmd.append(ENTRY)

    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print("\n打包失败")
            return False
    except Exception as e:
        print(f"\n打包失败: {e}")
        return False

    print("[4/4] 检查打包结果")
    exe_path = os.path.join("dist", f"{EXE_NAME}.exe")
    if not os.path.exists(exe_path):
        print("未找到生成的 EXE 文件")
        return False

    file_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print_header("打包成功")
    print(f"EXE: {exe_path}")
    print(f"大小: {file_size_mb:.1f} MB")

    # ---- generate file association registration scripts inside dist/ ----
    write_filetype_scripts(exe_path)
    write_usage_guide(exe_path)

    print("\n双击启动 .figbox 文件:")
    print("  1) 进入 dist/ 目录")
    print("  2) 右键 register_figbox.bat -> 以管理员身份运行")
    print("  3) 之后可以直接双击任意 .figbox 文件启动\n")
    print("如需取消文件关联，运行 unregister_figbox.bat（同样需管理员）")

    return True


def write_filetype_scripts(exe_path_in_dist):
    """Create register/unregister batch files alongside the EXE in dist/."""
    dist_dir = os.path.dirname(os.path.abspath(exe_path_in_dist))
    exe_basename = os.path.basename(exe_path_in_dist)

    # Use %~dp0 so the .bat is portable: it always resolves the EXE next to itself.
    register_content = (
        "@echo off\r\n"
        "REM Register .figbox -> FigBox.Project association\r\n"
        "REM Run as Administrator!\r\n"
        "setlocal\r\n"
        f"set EXE_PATH=%~dp0{exe_basename}\r\n"
        "if not exist \"%EXE_PATH%\" (\r\n"
        f"  echo [Error] {exe_basename} not found in this folder\r\n"
        "  pause & exit /b 1\r\n"
        ")\r\n"
        "echo Registering .figbox -> %EXE_PATH%\r\n"
        "reg add \"HKCR\\.figbox\" /ve /d \"FigBox.Project\" /f >nul\r\n"
        "reg add \"HKCR\\FigBox.Project\" /ve /d \"FigBox 学术组图项目\" /f >nul\r\n"
        "reg add \"HKCR\\FigBox.Project\\DefaultIcon\" /ve /d \"\\\"%EXE_PATH%\\\",0\" /f >nul\r\n"
        "reg add \"HKCR\\FigBox.Project\\shell\\open\\command\" /ve /d \"\\\"%EXE_PATH%\\\" \\\"%%1\\\"\" /f >nul\r\n"
        "echo Done. You can now double-click .figbox files.\r\n"
        "pause\r\n"
    )
    unregister_content = (
        "@echo off\r\n"
        "REM Unregister .figbox association. Run as Administrator!\r\n"
        "echo Removing .figbox association ...\r\n"
        "reg delete \"HKCR\\.figbox\" /f >nul 2>&1\r\n"
        "reg delete \"HKCR\\FigBox.Project\" /f >nul 2>&1\r\n"
        "echo Done.\r\n"
        "pause\r\n"
    )
    with open(os.path.join(dist_dir, "register_figbox.bat"), "w",
              encoding="ascii", errors="replace") as f:
        f.write(register_content)
    with open(os.path.join(dist_dir, "unregister_figbox.bat"), "w",
              encoding="ascii", errors="replace") as f:
        f.write(unregister_content)
    print(f"\n已生成: {os.path.join(dist_dir, 'register_figbox.bat')}")
    print(f"已生成: {os.path.join(dist_dir, 'unregister_figbox.bat')}")


def write_usage_guide(exe_path_in_dist):
    """在发布目录写入简明使用说明。"""
    dist_dir = os.path.dirname(os.path.abspath(exe_path_in_dist))
    guide_path = os.path.join(dist_dir, "使用说明.txt")
    content = """学术组图工具 V20 使用说明

1. 双击“学术组图工具V20.exe”即可打开软件，不需要安装 Python。
2. 单文件 EXE 首次启动需要解压运行组件，可能等待数秒。
3. 如需双击 .figbox 项目直接打开：右键 register_figbox.bat，选择“以管理员身份运行”。
4. 取消文件关联时，右键 unregister_figbox.bat，以管理员身份运行。
5. 本 EXE 未使用商业代码签名证书。若 Windows SmartScreen 提示，请确认文件来源和 SHA256 后选择继续运行。

同一个 EXE 也支持命令行：
  学术组图工具V20.exe compose --help
  学术组图工具V20.exe inspect --help
  学术组图工具V20.exe relayout --help
  学术组图工具V20.exe edit --help
  学术组图工具V20.exe boundary --help
  学术组图工具V20.exe canvas --help
  学术组图工具V20.exe export --help
  学术组图工具V20.exe preferences --help
"""
    with open(guide_path, "w", encoding="utf-8-sig", newline="\r\n") as file:
        file.write(content)
    print(f"已生成: {guide_path}")


if __name__ == "__main__":
    try:
        ok = build_exe()
    except KeyboardInterrupt:
        print("\n用户中断")
        ok = False
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback; traceback.print_exc()
        ok = False
    print("\n" + "=" * 70)
    input("按回车退出...")
    sys.exit(0 if ok else 1)
