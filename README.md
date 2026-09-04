# Figure Composer / 学术组图工具

Figure Composer 是用于科研论文图像排版与导出的 Windows 桌面软件。当前版本为 V20，既支持可视化拖拽编辑，也提供 Agent CLI，允许本地 AI Agent 在不控制鼠标的情况下完成组图、重排、编辑和导出。

## 下载

普通用户请前往 [GitHub Releases](https://github.com/liucheng2020/figure-composer/releases/latest) 下载 Windows 单文件 EXE。双击即可启动，无需安装 Python。

> EXE 当前未使用商业代码签名证书。Windows SmartScreen 可能显示“未知发布者”，请从本仓库 Release 下载并核对发布页提供的 SHA256。

## V20 主要功能

- 导入 PDF、PNG、JPG、TIFF 和 BMP。
- 规则网格、任意行列和 18 种上下/左右非对称智能网格。
- 等高填充、统一比例缩放和不缩放排列。
- 缩放、等宽等高、对齐、均分、定间距、旋转、移动和标签级联。
- PDF 边界扩展、紧缩和恢复。
- 单页矢量 PDF、PNG、TIFF、预览图和自包含 `.figbox` 项目导出。
- 自动生成布局清单、provenance、运行日志和验证报告。
- Agent CLI 支持 `compose`、`inspect`、`relayout`、`edit`、`boundary`、`canvas`、`export` 和 `preferences`。

完整说明见 [V20/README.md](V20/README.md)，GUI 与 CLI 功能对照见 [V20/CLI_FEATURE_MATRIX.md](V20/CLI_FEATURE_MATRIX.md)。

## 从源码运行

```powershell
cd V20
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_v20.py
```

## Agent CLI 示例

```powershell
python V20\agent_cli.py compose `
  --input "D:\论文图片" `
  --output "D:\论文图片\V20_Output" `
  --layout 4x4 `
  --fill-mode equal-height `
  --multipage error `
  --format pdf `
  --name Figure_1
```

CLI 默认不覆盖已有结果。显式使用 `--overwrite` 时，旧结果会移动到输出目录的 `.Trash`。

## 测试

```powershell
python -m pytest V20/tests -q
```

## 许可证

本项目允许个人在非商业的学习、科研和教育场景中使用。未经版权所有者事先书面许可，禁止盈利性使用、企业商业使用、收费服务、商业产品集成、转售或再许可。

这不是 OSI 认可的开源许可证。完整条款见 [LICENSE](LICENSE)。如需商业授权，请通过 GitHub 仓库联系版权所有者。
