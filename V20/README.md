# Figure Composer V20

学术组图工具 V20 是一个面向科研论文组图的桌面软件，并提供正式 Agent CLI。既可以在 GUI 中拖拽排版，也可以通过一条命令扫描 PDF、完成布局、导出结果并自动验证。

V20 的核心目标是让同一套排版与导出能力同时服务于人工编辑和 Agent 自动化，并保留每张图自身的宽高比例。

## Features

- 支持导入 PDF 和常见图片格式，在画布中自由拖拽、缩放和排列。
- 新增正式 `agent_cli.py`，无需控制鼠标即可自动组图。
- CLI 支持自动网格、规则网格、上下/左右非对称布局和中文布局别名。
- CLI 支持多页 PDF 的 `first`、`split`、`error` 三种策略。
- 每次 CLI 运行生成 `.figbox`、布局清单、provenance、预览、验证报告和日志。
- 支持 `.figbox` / `.figproj` 项目文件，并兼容 V18 项目。
- 新建项目默认边距为 5mm，旧项目打开时保留原有边距。
- 新增持久化设置窗口，可保存画布、边距、导出、标签、视图和自动备份默认值。
- 提供智能网格排版，可按指定行列或非对称模板整理选中图像。
- 支持等高填充宽度：通过在画布上拖一条横线指定总宽度，让选中图像等高铺满该宽度。
- 支持 `左二右一`、`左一右二`、`上二下一`、`上一下二`、`三列各二`、`上下各三` 等模板，并支持 `2+1` 这类自定义列模板。
- 支持标签级联联动，保持 A、B、C 等图注编号连续。
- 支持 PDF、PNG、TIFF 等导出方式，默认导出 DPI 为 1000。
- 导出时如果图片超出画布，导出画布会自动扩大并平移导出副本，确保所有图片都在导出画布内。
- 如果图片旁边存在 `<stem>.provenance.json`，V20 会自动读取并在导出组图时生成组合 provenance JSON。
- 对点很多的矢量图，推荐导出 PDF 以保留矢量质量。
- 支持 light、dark、cute 三种主题。
- 内置自动备份与项目恢复机制，降低误操作或异常退出造成的损失。

## Requirements

建议使用 Python 3.8 或更高版本。

主要依赖见 `requirements.txt`：

```text
PyQt5>=5.15.0
PyMuPDF>=1.18.0
Pillow>=8.0.0
```

如果需要打包为 Windows 可执行文件，还需要安装 `PyInstaller`。

## Installation

在项目目录中创建并启用虚拟环境：

```powershell
cd "D:\0 用AI做的项目\组图软件\V20"
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
python run_v20.py
```

使用 dark 主题：

```powershell
python run_v20.py dark
```

使用 cute 主题：

```powershell
python run_v20.py cute
```

直接打开已有项目：

```powershell
python run_v20.py "path\to\project.figbox"
```

指定主题并打开项目：

```powershell
python run_v20.py dark "path\to\project.figbox"
```

也可以在 Windows 中双击 `启动V20.bat` 启动。

## Agent CLI

最小调用示例：

```powershell
python agent_cli.py compose `
  --input "D:\论文图片" `
  --output "D:\论文图片\V20_Output" `
  --layout 4x4 `
  --name Figure_1
```

常用布局：

```text
auto                  自动选择每行数量
4x4                   最多 4 行 × 4 列
columns:2+1           左列 2 张，右列 1 张
rows:2+1              上排 2 张，下排 1 张
2+1                   columns:2+1 的简写
左二右一              columns:2+1 的中文别名
上二下一              rows:2+1 的中文别名
```

多页 PDF：

```powershell
--multipage first     仅使用第 1 页，默认
--multipage split     每一页拆成独立 panel
--multipage error     发现多页 PDF 立即报错
```

自定义顺序可通过 JSON 数组、每行一个文件名的文本文件，或逗号分隔文件名传入：

```powershell
--order "01_A.pdf,02_B.pdf,03_C.pdf"
```

CLI 默认拒绝覆盖已有结果。显式使用 `--overwrite` 时，旧结果会移动到输出目录的 `.Trash`。

### 全功能命令

```text
compose       从 PDF/PNG/JPG/TIFF/BMP 创建项目并导出
inspect       检查项目、素材、画布、设置和 panel 几何
relayout      对现有项目执行智能网格
edit          缩放、等宽等高、对齐、均分、间距、旋转、移动、尺寸、标签和删除
boundary      扩展、紧缩或恢复 PDF 边界
canvas        修改画布、边距、间距、DPI、标签和裁剪设置
export        从现有项目导出 PDF/PNG/TIF、FigBox、预览和验证报告
preferences   查看或修改 V20 GUI 持久化默认设置
```

智能网格的三种行为：

```powershell
--fill-mode equal-height    等高填满指定宽度，GUI 默认模式
--fill-mode uniform-scale   同一行使用统一缩放系数，保留相对大小
--fill-mode no-scale        只摆放，不改变 panel 大小
```

通过 `--span-left`、`--span-width` 和 `--top` 可以复现 GUI 鼠标画线指定位置和宽度的行为。完整 GUI→CLI 功能对照见 `CLI_FEATURE_MATRIX.md`。

## Smart Grid Workflow

V20 GUI 的重点功能是智能网格。

1. 在画布中选中需要排版的多张图。
2. 点击“智能网格”。
3. 选择行列数，例如 `1 x 4`、`2 x 2`、`3 x 2`，或选择非对称模板。
4. 如果勾选“等高填充宽度”，点击确认后在画布上拖一条横线。
5. 横线长度就是目标填充宽度，选中图像会按同一高度铺满该宽度。
6. 如果只是单击而不拖动，会使用当前画布的真实可用宽度，横版和竖版都适用。
7. 右键可取消当前画线操作。

等高填充会保留各图宽高比，不会强行拉伸图像内容。

非对称模板使用标签顺序填入位置。例如 `左二右一` 中，A/B 放左侧上下，C 放右侧大图位置，左右总高度会自动对齐；`上二下一` 中，A/B 放上排，C 放下排大图位置，两排都会铺满同一画布宽度。

## Export Notes

- PDF 导出会尽量保留矢量质量，适合论文投稿和后续编辑。
- PNG / TIFF 导出适合需要固定像素分辨率的场景。
- 默认 DPI 为 1000，可以根据期刊要求调整。
- 勾选自动裁剪时，导出画布会裁到图片包围盒；未勾选时保留原画布大小。
- 如果图片被拖到画布边界外，导出时仍会自动扩大或平移导出副本，确保图片不被裁掉；画布上的原始排版位置不会被改动。
- 普通导出和一键导出都会生成 `<export_base>_provenance.json`，把组图 panel 与原始 figure sidecar 关联起来。
- 对单细胞 UMAP、火山图等点很多的矢量图，优先推荐 PDF 导出。

## Figure Provenance

V20 支持读取每张图旁边的 provenance sidecar：

```text
01_umap.pdf
01_umap.provenance.json
```

导入图片时，如果 sidecar 存在，文件列表会显示 `provenance` 标记。保存 `.figbox` 时 provenance 会随项目保存；导出组图时会额外生成：

```text
<export_base>_provenance.json
```

用于后续大模型写结果报告时定位每个 panel 对应的代码、输入数据和分析上下文。

旧项目可以先用内置工具生成 sidecar：

```powershell
Rscript tools/generate_figure_provenance.R "D:\path\to\analysis_project"
```

该工具会输出总清单 `figure_provenance/figure_provenance_manifest.json`，并在每张图旁边写入 `<stem>.provenance.json`。

## Build Windows EXE

安装打包依赖：

```powershell
pip install pyinstaller
```

执行打包脚本：

```powershell
python build_exe_v20.py
```

打包完成后，输出文件会生成在 `dist/` 目录中。`build/`、`dist/` 和 `.spec` 文件属于构建产物，默认不会纳入 Git 管理。

## Project Structure

```text
V20/
├── run_v20.py                 # GUI 程序入口
├── agent_cli.py               # Agent 自动组图入口
├── project_ops.py             # 项目读取、布局和编辑操作
├── gui_editor.py              # 主界面与交互逻辑
├── canvas_widget.py           # 画布组件
├── layout_engine.py           # 排版算法
├── pdf_output.py              # 导出逻辑
├── pdf_utils.py               # PDF 工具函数
├── pdf_boundary_fix.py        # PDF 边界处理
├── project_io.py              # 项目文件读写
├── auto_backup.py             # 自动备份
├── themes.py                  # 主题系统
├── build_exe_v20.py           # Windows EXE 打包脚本
├── provenance_utils.py         # 图源信息 sidecar 与组图 provenance
├── tools/                     # 可复用工具脚本
├── tests/                     # 测试
└── V20更新说明.md              # V20 功能说明
```

## Testing

当前项目包含布局、设置和路径字段测试：

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

测试覆盖继承布局、V20 设置、全部智能网格、严格输入顺序、多页拆分、图片导入、项目编辑、边界持久化、导出和自动验证。

## Git Workflow

当前 Git 仓库根目录在 `组图软件/`，其中 `V18/`、`V19/` 和 `V20/` 是独立版本目录。

日常修改后：

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

建议用 Git tag 标记稳定版本：

```powershell
git tag v20.0
git push origin v20.0
```

后续大版本如果还需要独立目录，可继续新增 `V21/`；日常小改建议通过 Git 分支开发：

```powershell
git switch -c feature/new-layout-tool
```

完成后合并回 `main`。

## Notes

- `.Trash/`、`build/`、`dist/`、缓存文件和日志文件已通过 `.gitignore` 排除。
- 大体积打包文件建议放到 GitHub Releases，不建议直接提交到仓库。
- 项目文件 `.figbox` / `.figproj` 可用于保存和恢复组图工程。

## License

允许个人在非商业的学习、科研和教育场景中使用。未经版权所有者事先书面许可，禁止盈利性或商业使用。完整条款见仓库根目录 `LICENSE`。
