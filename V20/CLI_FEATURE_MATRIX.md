# V20 GUI 与 CLI 功能对照

## 输入与项目

| GUI 功能 | V20 CLI | 状态 |
|---|---|---|
| 浏览文件夹、重新扫描 | `compose --input` | 支持 |
| 导入 PDF | `compose` | 支持 |
| 导入 PNG/JPG/TIFF/BMP | `compose` 自动转换为内嵌 PDF | 支持 |
| 打开项目 | 所有带 `--project` 的命令 | 支持 |
| 保存项目 | `compose`、`relayout`、`edit`、`boundary`、`canvas` | 支持 |
| `.figbox` 自包含素材 | 自动打包 | 支持 |
| `.figproj` 兼容读取 | `inspect`、编辑和导出命令 | 支持 |
| 多页 PDF | `--multipage first/split/error` | 支持 |
| 自定义输入顺序 | `--order` | 支持 |

## 智能网格

| GUI 功能 | V20 CLI | 状态 |
|---|---|---|
| 任意行×列 | `--layout 4x4` 等 | 支持 |
| 等高填充宽度 | `--fill-mode equal-height` | 支持 |
| 同比例统一缩放 | `--fill-mode uniform-scale` | 支持 |
| 仅摆放不缩放 | `--fill-mode no-scale` | 支持 |
| 鼠标画线指定宽度 | `--span-left --span-width --top` | 支持 |
| 全部左右非对称模板 | 中文别名或 `columns:N+N` | 支持 |
| 全部上下非对称模板 | 中文别名或 `rows:N+N` | 支持 |
| 自定义列/行模板 | `columns:N+N`、`rows:N+N` | 支持 |

内置中文模板包括：左二右一、左一右二、左三右一、左一右三、左三右二、左二右三、左四右二、左二右四、三列各二、上二下一、上一下二、上三下一、上一下三、上三下二、上二下三、上四下二、上二下四、上下各三。

## 编辑

| GUI 功能 | V20 CLI | 状态 |
|---|---|---|
| 放大、缩小 | `edit --operation scale --factor` | 支持 |
| 等宽、等高 | `same-width`、`same-height` | 支持 |
| 左/右/顶/底对齐 | `align-left/right/top/bottom` | 支持 |
| 水平/垂直居中 | `align-h-center/v-center` | 支持 |
| 水平/垂直均分 | `distribute-horizontal/vertical` | 支持 |
| 水平/垂直定间距 | `spacing-horizontal/vertical --value` | 支持 |
| 旋转与重置 | `rotate --angle [--absolute]` | 支持 |
| 拖动位置 | `move --x/--y` 或 `--dx/--dy` | 支持 |
| 调整尺寸 | `resize --width/--height` | 支持 |
| 修改标签并级联 | `relabel --new-label` | 支持 |
| 删除并重新编号 | `delete` | 支持 |
| 选择部分 panel | `--select A,B,C` 或 `A-D` | 支持 |

## PDF 边界

| GUI 功能 | V20 CLI | 状态 |
|---|---|---|
| 四方向扩展 | `boundary --operation expand --directions` | 支持 |
| 四方向紧缩 | `boundary --operation shrink --directions` | 支持 |
| 恢复原始边界 | `boundary --operation restore` | 支持 |
| 派生 PDF 写入 FigBox | 自动嵌入 | 支持 |

## 画布、标签与导出

| GUI 功能 | V20 CLI | 状态 |
|---|---|---|
| 画布宽高、边距、间距、网格大小 | `canvas` | 支持 |
| DPI、自动裁剪 | `canvas`、`export` | 支持 |
| 标签字号、颜色、加粗、显示、距离 | `compose`、`canvas`、`export` | 支持 |
| PDF/PNG/TIF | `--format pdf/png/tif/all` | 支持 |
| 一键导出全部格式 | `export --format all` | 支持 |
| 预览 | 自动生成 `_preview.png` | 支持 |
| provenance | 自动生成 | 支持 |
| 输出验证 | 自动生成 `_validation.json` | 支持 |
| 查看项目状态 | `inspect` | 支持 |
| 持久化默认设置 | `preferences --set key=value` | 支持 |

## CLI 中不模拟的瞬时界面状态

主题、全屏、标尺、辅助线、网格吸附、文件夹窗口、剪贴板、画布标签页和鼠标撤销/重做属于 GUI 交互状态，不直接构成组图结果。CLI 采用“输入项目 → 新输出项目”的工作流，每一步保留独立 `.figbox` 和日志，因此无需模拟撤销栈；GUI 默认主题、标尺、辅助线、吸附和自动备份等设置仍可通过 `preferences` 管理。
