# Figure Composer V19

学术组图工具 V19 是一个面向科研论文组图的桌面软件，用于把 PDF、PNG、TIFF 等图像素材拖入画布后进行排版、对齐、标注和高分辨率导出。

V19 的核心目标是减少论文组图中反复缩放、对齐、铺满画布的手工操作，同时尽量保留每张图自身的宽高比例。

## Features

- 支持导入 PDF 和常见图片格式，在画布中自由拖拽、缩放和排列。
- 支持 `.figbox` / `.figproj` 项目文件，并兼容 V18 项目。
- 新建项目默认边距为 5mm，旧项目打开时保留原有边距。
- 新增持久化设置窗口，可保存画布、边距、导出、标签、视图和自动备份默认值。
- 提供智能网格排版，可按指定行列或非对称模板整理选中图像。
- 支持等高填充宽度：通过在画布上拖一条横线指定总宽度，让选中图像等高铺满该宽度。
- 支持 `左二右一`、`左一右二`、`左三右一`、`左三右二`、`三列各二` 等列模板，并支持 `2+1` 这类自定义模板。
- 支持标签级联联动，保持 A、B、C 等图注编号连续。
- 支持 PDF、PNG、TIFF 等导出方式，默认导出 DPI 为 1000。
- 导出的 `_info.md` 同时记录文件名和最早导入时的原始路径。
- 对点很多的矢量图，推荐导出 PDF 以保留矢量质量。
- 支持 light、dark、cute 三种主题。
- 内置自动备份与项目恢复机制，降低误操作或异常退出造成的损失。

## Requirements

建议使用 Python 3.8 或更高版本。

主要依赖见 `requirements.txt`：

```text
PyQt5>=5.15.0
PyMuPDF>=1.18.0
numpy>=1.19.0
Pillow>=8.0.0
```

如果需要打包为 Windows 可执行文件，还需要安装 `PyInstaller`。

## Installation

在项目目录中创建并启用虚拟环境：

```powershell
cd "D:\0 用AI做的项目\组图软件\V19"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果 PowerShell 阻止激活虚拟环境，可临时允许当前终端运行脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Usage

默认 light 主题启动：

```powershell
python run_v19.py
```

使用 dark 主题：

```powershell
python run_v19.py dark
```

使用 cute 主题：

```powershell
python run_v19.py cute
```

直接打开已有项目：

```powershell
python run_v19.py "path\to\project.figbox"
```

指定主题并打开项目：

```powershell
python run_v19.py dark "path\to\project.figbox"
```

也可以在 Windows 中双击 `启动V19.bat` 启动。

## Smart Grid Workflow

V19 的重点功能是智能网格。

1. 在画布中选中需要排版的多张图。
2. 点击“智能网格”。
3. 选择行列数，例如 `1 x 4`、`2 x 2`、`3 x 2`，或选择非对称模板。
4. 如果勾选“等高填充宽度”，点击确认后在画布上拖一条横线。
5. 横线长度就是目标填充宽度，选中图像会按同一高度铺满该宽度。
6. 如果只是单击而不拖动，会使用当前画布的真实可用宽度，横版和竖版都适用。
7. 右键可取消当前画线操作。

等高填充会保留各图宽高比，不会强行拉伸图像内容。

非对称模板使用标签顺序填入位置。例如 `左二右一` 中，A/B 放左侧上下，C 放右侧大图位置，左右总高度会自动对齐。

## Export Notes

- PDF 导出会尽量保留矢量质量，适合论文投稿和后续编辑。
- PNG / TIFF 导出适合需要固定像素分辨率的场景。
- 默认 DPI 为 1000，可以根据期刊要求调整。
- 对单细胞 UMAP、火山图等点很多的矢量图，优先推荐 PDF 导出。

## Build Windows EXE

安装打包依赖：

```powershell
pip install pyinstaller
```

执行打包脚本：

```powershell
python build_exe_v19.py
```

打包完成后，输出文件会生成在 `dist/` 目录中。`build/`、`dist/` 和 `.spec` 文件属于构建产物，默认不会纳入 Git 管理。

## Project Structure

```text
V19/
├── run_v19.py                 # 程序入口
├── gui_editor.py              # 主界面与交互逻辑
├── canvas_widget.py           # 画布组件
├── layout_engine.py           # 排版算法
├── pdf_output.py              # 导出逻辑
├── pdf_utils.py               # PDF 工具函数
├── pdf_boundary_fix.py        # PDF 边界处理
├── project_io.py              # 项目文件读写
├── auto_backup.py             # 自动备份
├── themes.py                  # 主题系统
├── build_exe_v19.py           # Windows EXE 打包脚本
├── tests/                     # 测试
├── docs/                      # 开发文档
└── V19更新说明.md              # V19 功能说明
```

## Testing

当前项目包含布局、设置和路径字段测试：

```powershell
python -m unittest tests.test_layout_v19
```

## Git Workflow

当前 Git 仓库根目录在 `组图软件/`，其中 `V18/` 和 `V19/` 是两个独立版本目录。

日常修改后：

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

建议用 Git tag 标记稳定版本：

```powershell
git tag v19.0
git push origin v19.0
```

后续大版本如果还需要独立目录，可继续新增 `V20/`；日常小改建议通过 Git 分支开发：

```powershell
git switch -c feature/new-layout-tool
```

完成后合并回 `main`。

## Notes

- `.Trash/`、`build/`、`dist/`、缓存文件和日志文件已通过 `.gitignore` 排除。
- 大体积打包文件建议放到 GitHub Releases，不建议直接提交到仓库。
- 项目文件 `.figbox` / `.figproj` 可用于保存和恢复组图工程。

