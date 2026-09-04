"""Figure Composer V20 Agent CLI。

通过一条命令调用 V20 现有布局、导出和 FigBox 模块，不依赖鼠标操作 GUI。
"""

import argparse
import json
import logging
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image

from gui_editor import calculate_export_canvas
from layout_engine import LayoutEngine, LayoutItem
from pdf_output import export_combined_image, export_combined_pdf
from pdf_utils import PDFInfo, parse_filename, scan_pdf_folder
from project_io import pack_figbox
from provenance_utils import load_figure_provenance, write_composition_provenance
from project_ops import (
    LoadedProject,
    apply_boundary,
    apply_transform,
    inspect_project,
    move_existing_to_trash,
    parse_selector,
    save_project,
    smart_relayout,
    update_project_settings,
)
from settings_manager import DEFAULT_SETTINGS, load_user_settings, save_settings


VERSION = "20.0"
LOGGER = logging.getLogger("figbox.agent_cli")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
LABEL_COLORS = {
    "black": ((0, 0, 0), "黑色"),
    "white": ((1, 1, 1), "白色"),
    "red": ((1, 0, 0), "红色"),
    "blue": ((0, 0, 1), "蓝色"),
    "green": ((0, 0.5, 0), "绿色"),
    "黑色": ((0, 0, 0), "黑色"),
    "白色": ((1, 1, 1), "白色"),
    "红色": ((1, 0, 0), "红色"),
    "蓝色": ((0, 0, 1), "蓝色"),
    "绿色": ((0, 0.5, 0), "绿色"),
}


@dataclass(frozen=True)
class LayoutSpec:
    """解析后的布局定义。"""

    kind: str
    counts: tuple
    source: str


CHINESE_LAYOUTS = {
    "左二右一": ("columns", (2, 1)),
    "左一右二": ("columns", (1, 2)),
    "左三右一": ("columns", (3, 1)),
    "左一右三": ("columns", (1, 3)),
    "左三右二": ("columns", (3, 2)),
    "左二右三": ("columns", (2, 3)),
    "左四右二": ("columns", (4, 2)),
    "左二右四": ("columns", (2, 4)),
    "三列各二": ("columns", (2, 2, 2)),
    "上二下一": ("rows", (2, 1)),
    "上一下二": ("rows", (1, 2)),
    "上三下一": ("rows", (3, 1)),
    "上一下三": ("rows", (1, 3)),
    "上三下二": ("rows", (3, 2)),
    "上二下三": ("rows", (2, 3)),
    "上四下二": ("rows", (4, 2)),
    "上二下四": ("rows", (2, 4)),
    "上下各三": ("rows", (3, 3)),
}


def configure_utf8_stdio():
    """统一命令行输出编码，避免 Windows 终端字符编码异常。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def panel_label(index):
    """生成 A、B、C……AA 形式的 panel 标签。"""
    value = index + 1
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(65 + remainder) + label
    return label


def parse_label_color(value):
    """把中英文颜色名转换为 PDF/Pillow 共用 RGB。"""
    key = str(value).strip().lower()
    if key not in LABEL_COLORS:
        key = str(value).strip()
    if key not in LABEL_COLORS:
        raise ValueError("标签颜色仅支持 black/white/red/blue/green 或对应中文")
    return LABEL_COLORS[key]


def scan_figure_folder(source_dir, work_dir):
    """扫描 PDF 和 GUI 支持的常见图片，并把图片转换为临时 PDF。"""
    source_dir = Path(source_dir)
    pdf_infos = scan_pdf_folder(str(source_dir))
    image_infos = []
    image_paths = sorted(
        [path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda path: path.name.casefold(),
    )
    for index, image_path in enumerate(image_paths):
        converted_path = Path(work_dir) / f"image_{index + 1:04d}_{image_path.stem}.pdf"
        with Image.open(image_path) as image:
            image.seek(0)
            rgb_image = image.convert("RGB")
            rgb_image.save(converted_path, "PDF", resolution=300.0)
        with fitz.open(converted_path) as document:
            rect = document[0].rect
        image_infos.append(PDFInfo(
            filepath=str(converted_path),
            filename=image_path.name,
            width=rect.width,
            height=rect.height,
            aspect_ratio=rect.width / rect.height if rect.height else 1.0,
            sort_key=parse_filename(image_path.name),
            original_path=str(image_path),
            provenance=load_figure_provenance(str(image_path)),
        ))
        print(f"[OK] Loaded image: {image_path.name}")
    return sorted(pdf_infos + image_infos, key=lambda info: info.sort_key)


def parse_counts(text):
    """解析 2+1 形式的正整数序列。"""
    parts = [part.strip() for part in text.split("+")]
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"无效布局数量: {text}")
    counts = tuple(int(part) for part in parts)
    if any(count <= 0 for count in counts):
        raise ValueError("布局中的每个数量必须大于 0")
    return counts


def parse_layout_spec(value, panel_count):
    """解析 auto、4x4、columns:2+1、rows:2+1 或中文布局名。"""
    text = value.strip()
    lower = text.lower().replace("×", "x")

    if text in CHINESE_LAYOUTS:
        kind, counts = CHINESE_LAYOUTS[text]
        if sum(counts) != panel_count:
            raise ValueError(f"布局 {text} 需要 {sum(counts)} 个 panel，实际为 {panel_count}")
        return LayoutSpec(kind, counts, text)

    if lower == "auto":
        columns = max(1, math.ceil(math.sqrt(panel_count)))
        counts = []
        remaining = panel_count
        while remaining:
            current = min(columns, remaining)
            counts.append(current)
            remaining -= current
        return LayoutSpec("grid", tuple(counts), text)

    grid_match = re.fullmatch(r"(?:grid:)?(\d+)x(\d+)", lower)
    if grid_match:
        rows = int(grid_match.group(1))
        columns = int(grid_match.group(2))
        if rows <= 0 or columns <= 0:
            raise ValueError("网格行列数必须大于 0")
        if rows * columns < panel_count:
            raise ValueError(f"布局 {text} 最多容纳 {rows * columns} 个 panel，实际为 {panel_count}")
        counts = []
        remaining = panel_count
        for _ in range(rows):
            if remaining <= 0:
                break
            current = min(columns, remaining)
            counts.append(current)
            remaining -= current
        return LayoutSpec("grid", tuple(counts), text)

    if lower.startswith("columns:"):
        counts = parse_counts(text.split(":", 1)[1])
        kind = "columns"
    elif lower.startswith("rows:"):
        counts = parse_counts(text.split(":", 1)[1])
        kind = "rows"
    elif re.fullmatch(r"\d+(?:\+\d+)+", text):
        counts = parse_counts(text)
        kind = "columns"
    else:
        raise ValueError(
            "不支持的布局。可用示例: auto、4x4、columns:2+1、rows:2+1、左二右一"
        )

    if sum(counts) != panel_count:
        raise ValueError(f"布局 {text} 需要 {sum(counts)} 个 panel，实际为 {panel_count}")
    return LayoutSpec(kind, counts, text)


def read_order(order_value):
    """读取 JSON、文本或逗号分隔的文件名顺序。"""
    if not order_value:
        return None
    order_path = Path(order_value)
    if order_path.is_file():
        if order_path.suffix.lower() == ".json":
            with order_path.open("r", encoding="utf-8") as file:
                names = json.load(file)
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise ValueError("顺序 JSON 必须是文件名字符串数组")
            return names
        with order_path.open("r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    return [name.strip() for name in order_value.split(",") if name.strip()]


def apply_order(pdf_infos, names):
    """按用户给出的完整文件名列表重排输入。"""
    if names is None:
        return pdf_infos
    lookup = {info.filename.casefold(): info for info in pdf_infos}
    requested = [name.casefold() for name in names]
    if len(requested) != len(set(requested)):
        raise ValueError("顺序列表包含重复文件名")
    missing = [name for name in names if name.casefold() not in lookup]
    extra = [info.filename for info in pdf_infos if info.filename.casefold() not in requested]
    if missing or extra:
        raise ValueError(f"顺序列表必须完整匹配输入 PDF；不存在={missing}，未列出={extra}")
    return [lookup[name] for name in requested]


def expand_source_pages(pdf_infos, multipage, work_dir):
    """根据多页策略生成实际参与组图的 PDFInfo 列表。"""
    panels = []
    for source_info in pdf_infos:
        provenance = source_info.provenance or load_figure_provenance(
            source_info.original_path or source_info.filepath)
        with fitz.open(source_info.filepath) as document:
            page_count = len(document)
            if page_count == 0:
                raise ValueError(f"PDF 没有页面: {source_info.filepath}")
            if multipage == "error" and page_count > 1:
                raise ValueError(f"检测到多页 PDF: {source_info.filename}，共 {page_count} 页")

            page_indexes = range(page_count) if multipage == "split" else range(1)
            for page_index in page_indexes:
                if multipage == "split":
                    output_name = f"{Path(source_info.filename).stem}__page_{page_index + 1:02d}.pdf"
                    page_path = work_dir / f"{len(panels) + 1:04d}_{output_name}"
                    page_document = fitz.open()
                    page_document.insert_pdf(document, from_page=page_index, to_page=page_index)
                    page_document.save(str(page_path), garbage=4, deflate=True)
                    page_document.close()
                    rect = document[page_index].rect
                    panel_info = PDFInfo(
                        filepath=str(page_path),
                        filename=output_name,
                        width=rect.width,
                        height=rect.height,
                        aspect_ratio=rect.width / rect.height if rect.height else 1.0,
                        sort_key=(len(panels),),
                        original_path=source_info.filepath,
                        provenance=provenance,
                    )
                else:
                    panel_info = source_info
                    panel_info.provenance = provenance

                panel_info.source_filename = source_info.filename
                panel_info.source_page = page_index + 1
                panel_info.source_page_count = page_count
                panels.append(panel_info)
    return panels


def build_layouts(pdf_infos, layout_spec, canvas_width, canvas_height, margin, spacing):
    """调用 V20 布局引擎生成 panel 几何。"""
    initial = [
        LayoutItem(
            pdf_info=info,
            x=0.0,
            y=0.0,
            width=info.width,
            height=info.height,
            label=panel_label(index),
        )
        for index, info in enumerate(pdf_infos)
    ]
    engine = LayoutEngine(canvas_width, canvas_height, margin_mm=margin, spacing_mm=spacing)
    if layout_spec.kind == "columns":
        return engine.asymmetric_columns(initial, list(layout_spec.counts))
    return engine.asymmetric_rows(initial, list(layout_spec.counts))


def build_project_data(layouts, canvas_width, canvas_height, args):
    """生成 V20 GUI 可重新打开的项目数据。"""
    _, project_color = parse_label_color(args.label_color)
    return {
        "version": VERSION,
        "canvas_name": args.name,
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "settings": {
            "margin": args.margin,
            "spacing": args.spacing,
            "grid_size": 5,
            "label_fontsize": args.label_fontsize,
            "label_visible": args.label_visible,
            "label_bold": args.label_bold,
            "label_color": project_color,
            "label_offset": args.label_offset,
            "dpi": args.dpi,
            "export_format": "PDF矢量" if args.format == "pdf" else args.format.upper(),
            "auto_crop": not args.preserve_canvas,
        },
        "layouts": [
            {
                "pdf_path": item.pdf_info.filepath,
                "original_path": item.pdf_info.original_path or item.pdf_info.filepath,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
                "rotation": item.rotation,
                "label": item.label,
                "expand_boundary": item.pdf_info.expand_boundary,
                "expanded_filepath": item.pdf_info.expanded_filepath,
                "cumulative_margin": item.pdf_info.cumulative_margin,
                "provenance": item.pdf_info.provenance,
                "source_page": getattr(item.pdf_info, "source_page", 1),
                "source_page_count": getattr(item.pdf_info, "source_page_count", 1),
            }
            for item in layouts
        ],
    }


def output_paths(output_dir, name, output_format):
    """列出本次运行会产生的正式文件。"""
    paths = {
        "figbox": output_dir / f"{name}.figbox",
        "layout": output_dir / f"{name}_layout.json",
        "provenance": output_dir / f"{name}_provenance.json",
        "preview": output_dir / f"{name}_preview.png",
        "validation": output_dir / f"{name}_validation.json",
        "log": output_dir / f"{name}_run.log",
    }
    if output_format in ("pdf", "all"):
        paths["pdf"] = output_dir / f"{name}.pdf"
    if output_format in ("png", "all"):
        paths["png"] = output_dir / f"{name}.png"
    if output_format in ("tif", "all"):
        paths["tif"] = output_dir / f"{name}.tif"
    return paths


def protect_existing_outputs(paths, overwrite):
    """默认拒绝覆盖；显式覆盖时把旧文件移动到输出目录的 .Trash。"""
    existing = [path for path in paths.values() if path.exists()]
    if not existing:
        return
    if not overwrite:
        joined = "\n".join(str(path) for path in existing)
        raise FileExistsError(f"输出已存在；如需重跑请使用 --overwrite：\n{joined}")
    trash_dir = next(iter(paths.values())).parent / ".Trash"
    trash_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path in existing:
        destination = trash_dir / f"{path.stem}_{stamp}{path.suffix}"
        shutil.move(str(path), str(destination))


def setup_logging(log_path):
    """同时记录终端与 UTF-8 日志。"""
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)


def close_logging():
    """释放日志文件句柄，避免 Windows 阻止后续移动或清理目录。"""
    for handler in list(LOGGER.handlers):
        handler.flush()
        handler.close()
        LOGGER.removeHandler(handler)


def rectangles_overlap(first, second, tolerance=1e-6):
    """判断两个 panel 矩形是否发生实质重叠。"""
    overlap_x = min(first.x + first.width, second.x + second.width) - max(first.x, second.x)
    overlap_y = min(first.y + first.height, second.y + second.height) - max(first.y, second.y)
    return overlap_x > tolerance and overlap_y > tolerance


def validate_outputs(layouts, canvas_width, canvas_height, paths):
    """检查边界、重叠、导出文件、PDF 和 FigBox 结构。"""
    errors = []
    for item in layouts:
        if item.x < -1e-6 or item.y < -1e-6:
            errors.append(f"panel {item.label} 超出左侧或顶部边界")
        if item.x + item.width > canvas_width + 1e-6:
            errors.append(f"panel {item.label} 超出右侧边界")
        if item.y + item.height > canvas_height + 1e-6:
            errors.append(f"panel {item.label} 超出底部边界")

    overlaps = []
    for index, first in enumerate(layouts):
        for second in layouts[index + 1:]:
            if rectangles_overlap(first, second):
                overlaps.append(f"{first.label}-{second.label}")
    if overlaps:
        errors.append(f"panel 重叠: {', '.join(overlaps)}")

    for key, path in paths.items():
        if key in ("log", "validation"):
            continue
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"输出缺失或为空: {path}")

    pdf_metadata = None
    if "pdf" in paths and paths["pdf"].exists():
        with fitz.open(paths["pdf"]) as document:
            rect = document[0].rect if len(document) else None
            pdf_metadata = {
                "pages": len(document),
                "width_mm": round(rect.width * 25.4 / 72, 3) if rect else None,
                "height_mm": round(rect.height * 25.4 / 72, 3) if rect else None,
            }
            if len(document) != 1:
                errors.append(f"输出 PDF 应为 1 页，实际为 {len(document)} 页")

    figbox_metadata = None
    if paths["figbox"].exists():
        with zipfile.ZipFile(paths["figbox"]) as archive:
            names = archive.namelist()
            if "project.json" not in names or "manifest.json" not in names:
                errors.append("FigBox 缺少 project.json 或 manifest.json")
            project = json.loads(archive.read("project.json").decode("utf-8"))
            asset_count = len([name for name in names if name.startswith("assets/") and not name.endswith("/")])
            layout_count = len(project.get("layouts", []))
            figbox_metadata = {"layouts": layout_count, "assets": asset_count}
            if layout_count != len(layouts) or asset_count < len(layouts):
                errors.append(
                    f"FigBox 数量不一致: layouts={layout_count}, assets={asset_count}, panels={len(layouts)}"
                )

    return {
        "status": "PASS" if not errors else "FAIL",
        "panel_count": len(layouts),
        "labels": [item.label for item in layouts],
        "canvas_width_mm": canvas_width,
        "canvas_height_mm": canvas_height,
        "overlaps": overlaps,
        "pdf": pdf_metadata,
        "figbox": figbox_metadata,
        "errors": errors,
    }


def write_layout_manifest(path, args, layout_spec, layouts, canvas_width, canvas_height, outputs):
    """保存完整输入顺序、页码、布局参数和 panel 坐标。"""
    manifest = {
        "schema_version": "1.0",
        "tool": "Figure Composer V20 Agent CLI",
        "tool_version": VERSION,
        "input_dir": str(Path(args.input).resolve()),
        "output_dir": str(Path(args.output).resolve()),
        "layout": {
            "requested": layout_spec.source,
            "kind": layout_spec.kind,
            "counts": list(layout_spec.counts),
            "fill_mode": args.fill_mode,
            "span_left_mm": args.span_left,
            "span_width_mm": args.span_width,
            "top_mm": args.top,
            "canvas_width_mm": canvas_width,
            "canvas_height_mm": canvas_height,
            "margin_mm": args.margin,
            "spacing_mm": args.spacing,
            "padding_mm": args.padding,
            "preserve_canvas": args.preserve_canvas,
        },
        "multipage": args.multipage,
        "format": args.format,
        "outputs": {key: str(value) for key, value in outputs.items()},
        "panels": [
            {
                "label": item.label,
                "filename": item.pdf_info.filename,
                "source_filename": getattr(item.pdf_info, "source_filename", item.pdf_info.filename),
                "source_path": item.pdf_info.original_path or item.pdf_info.filepath,
                "source_page": getattr(item.pdf_info, "source_page", 1),
                "source_page_count": getattr(item.pdf_info, "source_page_count", 1),
                "x_mm": round(item.x, 4),
                "y_mm": round(item.y, 4),
                "width_mm": round(item.width, 4),
                "height_mm": round(item.height, 4),
            }
            for item in layouts
        ],
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)


def _compose(args):
    """执行完整自动组图流程。"""
    source_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"输入目录不存在: {source_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir, args.name, args.format)
    protect_existing_outputs(paths, args.overwrite)
    setup_logging(paths["log"])

    with tempfile.TemporaryDirectory(prefix="figbox_v20_") as work_dir_text:
        work_dir = Path(work_dir_text)
        LOGGER.info("[1/7] 扫描输入 PDF 和图片")
        source_infos = scan_figure_folder(source_dir, work_dir)
        source_infos = apply_order(source_infos, read_order(args.order))
        if not source_infos:
            raise ValueError(f"输入目录没有可用 PDF 或图片: {source_dir}")
        panel_infos = expand_source_pages(source_infos, args.multipage, work_dir)
        LOGGER.info("[2/7] 确认 panel：%d 个", len(panel_infos))

        layout_spec = parse_layout_spec(args.layout, len(panel_infos))
        layouts = [
            LayoutItem(
                info, 0.0, 0.0, info.width, info.height,
                0.0, panel_label(index))
            for index, info in enumerate(panel_infos)
        ]
        smart_relayout(
            layouts,
            list(range(len(layouts))),
            layout_spec,
            args.fill_mode,
            args.canvas_width,
            args.canvas_height,
            args.margin,
            args.spacing,
            args.span_left,
            args.span_width,
            args.top,
        )
        layouts, canvas_width, canvas_height = calculate_export_canvas(
            layouts,
            args.canvas_width,
            args.canvas_height,
            padding=args.padding,
            auto_crop=not args.preserve_canvas,
            label_visible=args.label_visible,
            label_fontsize=args.label_fontsize,
            label_offset=args.label_offset,
            label_bold=args.label_bold,
        )
        LOGGER.info(
            "[3/7] 完成布局：%s，画布 %.0f x %.0f mm",
            args.layout,
            canvas_width,
            canvas_height,
        )

        label_color, _ = parse_label_color(args.label_color)
        if "pdf" in paths:
            export_combined_pdf(
                layouts,
                canvas_width,
                canvas_height,
                str(paths["pdf"]),
                dpi=args.dpi,
                label_bold=args.label_bold,
                label_offset=args.label_offset,
                label_fontsize=args.label_fontsize,
                label_color=label_color,
                label_visible=args.label_visible,
            )
        if "png" in paths:
            export_combined_image(
                layouts,
                canvas_width,
                canvas_height,
                str(paths["png"]),
                image_format="png",
                dpi=args.dpi,
                label_bold=args.label_bold,
                label_offset=args.label_offset,
                label_fontsize=args.label_fontsize,
                label_color=label_color,
                label_visible=args.label_visible,
            )
        if "tif" in paths:
            export_combined_image(
                layouts,
                canvas_width,
                canvas_height,
                str(paths["tif"]),
                image_format="tif",
                dpi=args.dpi,
                label_bold=args.label_bold,
                label_offset=args.label_offset,
                label_fontsize=args.label_fontsize,
                label_color=label_color,
                label_visible=args.label_visible,
            )
        LOGGER.info("[4/7] 已导出正式组图")

        project_data = build_project_data(layouts, canvas_width, canvas_height, args)
        pack_figbox(
            str(paths["figbox"]),
            project_data,
            [item.pdf_info.filepath for item in layouts],
        )
        LOGGER.info("[5/7] 已保存可编辑 FigBox 项目")

        write_layout_manifest(
            paths["layout"],
            args,
            layout_spec,
            layouts,
            canvas_width,
            canvas_height,
            paths,
        )
        write_composition_provenance(
            str(output_dir / args.name),
            args.name,
            layouts,
            project_root=str(source_dir),
        )
        export_combined_image(
            layouts,
            canvas_width,
            canvas_height,
            str(paths["preview"]),
            image_format="png",
            dpi=args.preview_dpi,
            label_bold=args.label_bold,
            label_offset=args.label_offset,
            label_fontsize=args.label_fontsize,
            label_color=label_color,
            label_visible=args.label_visible,
        )
        LOGGER.info("[6/7] 已生成清单、provenance 和预览")

        validation = validate_outputs(layouts, canvas_width, canvas_height, paths)
        with paths["validation"].open("w", encoding="utf-8") as file:
            json.dump(validation, file, ensure_ascii=False, indent=2)
        LOGGER.info("[7/7] V20_VALIDATION=%s", validation["status"])
        if validation["status"] != "PASS":
            raise RuntimeError("输出验证失败: " + "; ".join(validation["errors"]))

    close_logging()
    return paths


def compose(args):
    """保证成功或失败时都释放 Windows 日志文件句柄。"""
    try:
        return _compose(args)
    finally:
        if LOGGER.handlers:
            close_logging()


def handle_inspect(args):
    """检查 FigBox/figproj 项目结构。"""
    with LoadedProject.open(args.project) as session:
        result = inspect_project(session)
    if args.json:
        json_path = Path(args.json).resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        result["json"] = str(json_path)
    return result


def handle_relayout(args):
    """重新排列现有项目的全部或部分 panel。"""
    with LoadedProject.open(args.project) as session:
        selected_indices = parse_selector(session.layouts, args.select)
        layout_spec = parse_layout_spec(args.layout, len(selected_indices))
        settings = session.data.get("settings", {})
        canvas_width = args.canvas_width or float(session.data.get("canvas_width", 297))
        canvas_height = args.canvas_height or float(session.data.get("canvas_height", 210))
        margin = args.margin if args.margin is not None else float(settings.get("margin", 5))
        spacing = args.spacing if args.spacing is not None else float(settings.get("spacing", 5))
        smart_relayout(
            session.layouts,
            selected_indices,
            layout_spec,
            args.fill_mode,
            canvas_width,
            canvas_height,
            margin,
            spacing,
            args.span_left,
            args.span_width,
            args.top,
        )
        session.data["canvas_width"] = canvas_width
        session.data["canvas_height"] = canvas_height
        session.data.setdefault("settings", {})["margin"] = margin
        session.data.setdefault("settings", {})["spacing"] = spacing
        if args.fit_canvas:
            session.layouts, fitted_width, fitted_height = calculate_export_canvas(
                session.layouts, canvas_width, canvas_height,
                padding=args.padding, auto_crop=True,
                label_visible=bool(settings.get("label_visible", True)),
                label_fontsize=int(settings.get("label_fontsize", 12)),
                label_offset=float(settings.get("label_offset", 0.25)),
                label_bold=bool(settings.get("label_bold", True)))
            session.data["canvas_width"] = fitted_width
            session.data["canvas_height"] = fitted_height
        output = save_project(session, args.output, args.overwrite)
    return {"project": output, "layout": args.layout, "fill_mode": args.fill_mode}


def handle_edit(args):
    """执行对齐、缩放、旋转、间距、标签和删除等项目编辑。"""
    with LoadedProject.open(args.project) as session:
        selected_indices = parse_selector(session.layouts, args.select)
        apply_transform(
            session.layouts,
            selected_indices,
            args.operation,
            factor=args.factor,
            value=args.value,
            angle=args.angle,
            absolute=args.absolute,
            x=args.x,
            y=args.y,
            dx=args.dx,
            dy=args.dy,
            width=args.width,
            height=args.height,
            new_label=args.new_label,
        )
        output = save_project(session, args.output, args.overwrite)
    return {"project": output, "operation": args.operation, "selected": args.select}


def handle_boundary(args):
    """扩展、紧缩或恢复 PDF 边界。"""
    with LoadedProject.open(args.project) as session:
        selected_indices = parse_selector(session.layouts, args.select)
        apply_boundary(
            session.layouts,
            selected_indices,
            args.operation,
            args.points,
            args.directions,
            session.temp_dir,
        )
        output = save_project(session, args.output, args.overwrite)
    return {"project": output, "operation": args.operation, "selected": args.select}


def handle_canvas(args):
    """更新项目画布、标签与导出设置。"""
    label_color = args.label_color
    if label_color is not None:
        _, label_color = parse_label_color(label_color)
    with LoadedProject.open(args.project) as session:
        update_project_settings(
            session,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            margin=args.margin,
            spacing=args.spacing,
            grid_size=args.grid_size,
            dpi=args.dpi,
            label_fontsize=args.label_fontsize,
            label_visible=args.label_visible,
            label_bold=args.label_bold,
            label_color=label_color,
            label_offset=args.label_offset,
            auto_crop=args.auto_crop,
        )
        output = save_project(session, args.output, args.overwrite)
    return {"project": output, "settings": "updated"}


def project_export_manifest(session, layouts, paths, canvas_width, canvas_height):
    """生成现有项目导出的布局清单。"""
    return {
        "schema_version": "1.0",
        "tool": "Figure Composer V20 Agent CLI",
        "tool_version": VERSION,
        "source_project": str(session.source_path),
        "canvas_width_mm": canvas_width,
        "canvas_height_mm": canvas_height,
        "outputs": {key: str(path) for key, path in paths.items()},
        "panels": [
            {
                "label": item.label,
                "filename": item.pdf_info.filename,
                "source_path": item.pdf_info.original_path,
                "x_mm": item.x,
                "y_mm": item.y,
                "width_mm": item.width,
                "height_mm": item.height,
                "rotation": item.rotation,
            }
            for item in layouts
        ],
    }


def handle_export(args):
    """从现有 FigBox 项目导出正式结果、预览和验证报告。"""
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    name = args.name or Path(args.project).stem
    paths = output_paths(output_dir, name, args.format)
    protect_existing_outputs(paths, args.overwrite)
    setup_logging(paths["log"])

    with LoadedProject.open(args.project) as session:
        settings = session.data.get("settings", {})
        source_width = float(session.data.get("canvas_width", 297))
        source_height = float(session.data.get("canvas_height", 210))
        auto_crop = bool(settings.get("auto_crop", True)) if args.crop == "project" else args.crop == "auto"
        dpi = args.dpi or int(settings.get("dpi", 1000))
        label_bold = bool(settings.get("label_bold", True))
        label_visible = bool(settings.get("label_visible", True))
        label_fontsize = int(settings.get("label_fontsize", 12))
        label_offset = float(settings.get("label_offset", 0.25))
        label_color, _ = parse_label_color(settings.get("label_color", "黑色"))
        layouts, canvas_width, canvas_height = calculate_export_canvas(
            session.layouts, source_width, source_height,
            padding=args.padding, auto_crop=auto_crop,
            label_visible=label_visible,
            label_fontsize=label_fontsize,
            label_offset=label_offset,
            label_bold=label_bold)

        LOGGER.info("[1/4] 导出项目组图")
        if "pdf" in paths:
            export_combined_pdf(
                layouts, canvas_width, canvas_height, str(paths["pdf"]), dpi,
                label_bold, label_offset, label_fontsize, label_color, label_visible)
        if "png" in paths:
            export_combined_image(
                layouts, canvas_width, canvas_height, str(paths["png"]), "png", dpi,
                label_bold, label_offset, label_fontsize, label_color, label_visible)
        if "tif" in paths:
            export_combined_image(
                layouts, canvas_width, canvas_height, str(paths["tif"]), "tif", dpi,
                label_bold, label_offset, label_fontsize, label_color, label_visible)

        LOGGER.info("[2/4] 保存项目副本和来源记录")
        save_project(session, paths["figbox"], overwrite=False)
        with paths["layout"].open("w", encoding="utf-8") as file:
            json.dump(
                project_export_manifest(session, layouts, paths, canvas_width, canvas_height),
                file, ensure_ascii=False, indent=2)
        write_composition_provenance(
            str(output_dir / name), name, layouts, project_root=str(session.source_path.parent))
        export_combined_image(
            layouts, canvas_width, canvas_height, str(paths["preview"]), "png",
            args.preview_dpi, label_bold, label_offset, label_fontsize,
            label_color, label_visible)

        LOGGER.info("[3/4] 验证导出结构")
        validation = validate_outputs(layouts, canvas_width, canvas_height, paths)
        with paths["validation"].open("w", encoding="utf-8") as file:
            json.dump(validation, file, ensure_ascii=False, indent=2)
        LOGGER.info("[4/4] V20_VALIDATION=%s", validation["status"])
        if validation["status"] != "PASS":
            raise RuntimeError("输出验证失败: " + "; ".join(validation["errors"]))
    close_logging()
    return paths


def parse_preference_value(key, value):
    """按默认设置类型解析 key=value。"""
    if key not in DEFAULT_SETTINGS:
        raise ValueError(f"未知设置项: {key}")
    default = DEFAULT_SETTINGS[key]
    if isinstance(default, bool):
        lower = value.lower()
        if lower not in ("true", "false"):
            raise ValueError(f"布尔设置必须为 true 或 false: {key}")
        return lower == "true"
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value)
    return value


def handle_preferences(args):
    """查看或修改 V20 GUI 的持久化默认设置。"""
    settings = load_user_settings()
    for assignment in args.set or []:
        if "=" not in assignment:
            raise ValueError(f"设置必须采用 key=value: {assignment}")
        key, value = assignment.split("=", 1)
        key = key.strip()
        settings[key] = parse_preference_value(key, value.strip())
    if args.set:
        settings = save_settings(settings)
    return settings


def build_parser():
    """构造命令行参数。"""
    parser = argparse.ArgumentParser(prog="agent_cli.py", description="Figure Composer V20 Agent CLI")
    parser.add_argument("--version", action="version", version=f"Figure Composer V{VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compose_parser = subparsers.add_parser("compose", help="自动扫描、排版、导出和验证 PDF/图片")
    compose_parser.add_argument("--input", required=True, help="包含 PDF 或常见图片的输入目录")
    compose_parser.add_argument("--output", required=True, help="独立输出目录")
    compose_parser.add_argument("--name", default="Figure", help="输出文件基础名")
    compose_parser.add_argument(
        "--layout",
        default="auto",
        help="auto、4x4、columns:2+1、rows:2+1、2+1 或中文布局名",
    )
    compose_parser.add_argument(
        "--fill-mode", choices=("equal-height", "uniform-scale", "no-scale"),
        default="equal-height", help="智能网格填充模式")
    compose_parser.add_argument("--span-left", type=float, help="模拟画线起点 x，单位 mm")
    compose_parser.add_argument("--span-width", type=float, help="模拟画线宽度，单位 mm")
    compose_parser.add_argument("--top", type=float, help="布局顶部 y，单位 mm")
    compose_parser.add_argument("--order", help="完整文件顺序：JSON、文本文件或逗号分隔文件名")
    compose_parser.add_argument(
        "--multipage",
        choices=("first", "split", "error"),
        default="first",
        help="多页 PDF 策略：仅首页、拆页、报错",
    )
    compose_parser.add_argument("--format", choices=("pdf", "png", "tif", "all"), default="pdf")
    compose_parser.add_argument("--canvas-width", type=float, default=297.0, help="目标画布宽度 mm")
    compose_parser.add_argument("--canvas-height", type=float, default=210.0, help="目标画布高度 mm")
    compose_parser.add_argument("--margin", type=float, default=5.0, help="布局边距 mm")
    compose_parser.add_argument("--spacing", type=float, default=5.0, help="panel 间距 mm")
    compose_parser.add_argument("--padding", type=float, default=2.0, help="自动裁剪后的外侧留白 mm")
    compose_parser.add_argument("--dpi", type=int, default=1000, help="正式光栅导出 DPI")
    compose_parser.add_argument("--preview-dpi", type=int, default=120, help="预览 PNG DPI")
    compose_parser.add_argument("--label-fontsize", type=int, default=12, help="panel 标签字号 pt")
    compose_parser.add_argument("--label-color", default="black", help="panel 标签颜色")
    compose_parser.add_argument("--label-offset", type=float, default=0.25, help="panel 标签距离 mm")
    compose_parser.add_argument("--label-regular", dest="label_bold", action="store_false", help="标签不加粗")
    compose_parser.add_argument("--hide-labels", dest="label_visible", action="store_false", help="隐藏 panel 标签")
    compose_parser.set_defaults(label_bold=True, label_visible=True)
    compose_parser.add_argument("--preserve-canvas", action="store_true", help="保留目标画布，不自动裁剪空白")
    compose_parser.add_argument("--overwrite", action="store_true", help="把同名旧结果移动到 .Trash 后重跑")
    compose_parser.set_defaults(handler=compose)

    inspect_parser = subparsers.add_parser("inspect", help="检查项目画布、设置、素材和 panel 几何")
    inspect_parser.add_argument("--project", required=True, help="输入 .figbox 或 .figproj")
    inspect_parser.add_argument("--json", help="可选 JSON 输出路径")
    inspect_parser.set_defaults(handler=handle_inspect)

    relayout_parser = subparsers.add_parser("relayout", help="对现有项目执行全部智能网格布局")
    relayout_parser.add_argument("--project", required=True)
    relayout_parser.add_argument("--output", required=True, help="新的 .figbox 输出")
    relayout_parser.add_argument("--select", default="all", help="all、A,B,C 或 A-D")
    relayout_parser.add_argument("--layout", required=True, help="4x4、columns:2+1、rows:2+1 或中文布局")
    relayout_parser.add_argument(
        "--fill-mode", choices=("equal-height", "uniform-scale", "no-scale"),
        default="equal-height", help="等高填充、统一比例填充或仅摆放不缩放")
    relayout_parser.add_argument("--canvas-width", type=float)
    relayout_parser.add_argument("--canvas-height", type=float)
    relayout_parser.add_argument("--margin", type=float)
    relayout_parser.add_argument("--spacing", type=float)
    relayout_parser.add_argument("--span-left", type=float, help="模拟画线起点 x，单位 mm")
    relayout_parser.add_argument("--span-width", type=float, help="模拟画线宽度，单位 mm")
    relayout_parser.add_argument("--top", type=float, help="布局顶部 y，单位 mm")
    relayout_parser.add_argument("--fit-canvas", action="store_true", help="完成后让画布包住所有 panel")
    relayout_parser.add_argument("--padding", type=float, default=2.0)
    relayout_parser.add_argument("--overwrite", action="store_true")
    relayout_parser.set_defaults(handler=handle_relayout)

    edit_parser = subparsers.add_parser("edit", help="执行缩放、等宽等高、对齐、均分、间距、旋转和标签操作")
    edit_parser.add_argument("--project", required=True)
    edit_parser.add_argument("--output", required=True, help="新的 .figbox 输出")
    edit_parser.add_argument("--select", default="all")
    edit_parser.add_argument("--operation", required=True, choices=(
        "scale", "same-width", "same-height",
        "align-left", "align-right", "align-top", "align-bottom",
        "align-h-center", "align-v-center",
        "distribute-horizontal", "distribute-vertical",
        "spacing-horizontal", "spacing-vertical",
        "rotate", "move", "resize", "delete", "relabel"))
    edit_parser.add_argument("--factor", type=float, default=1.05)
    edit_parser.add_argument("--value", type=float, default=5.0, help="间距 mm")
    edit_parser.add_argument("--angle", type=float, default=90.0)
    edit_parser.add_argument("--absolute", action="store_true", help="旋转角度使用绝对值")
    edit_parser.add_argument("--x", type=float)
    edit_parser.add_argument("--y", type=float)
    edit_parser.add_argument("--dx", type=float, default=0.0)
    edit_parser.add_argument("--dy", type=float, default=0.0)
    edit_parser.add_argument("--width", type=float)
    edit_parser.add_argument("--height", type=float)
    edit_parser.add_argument("--new-label")
    edit_parser.add_argument("--overwrite", action="store_true")
    edit_parser.set_defaults(handler=handle_edit)

    boundary_parser = subparsers.add_parser("boundary", help="扩展、紧缩或恢复 PDF 边界")
    boundary_parser.add_argument("--project", required=True)
    boundary_parser.add_argument("--output", required=True, help="新的 .figbox 输出")
    boundary_parser.add_argument("--select", default="all")
    boundary_parser.add_argument("--operation", required=True, choices=("expand", "shrink", "restore"))
    boundary_parser.add_argument("--points", type=float, default=20.0)
    boundary_parser.add_argument("--directions", default="left,right,top,bottom")
    boundary_parser.add_argument("--overwrite", action="store_true")
    boundary_parser.set_defaults(handler=handle_boundary)

    canvas_parser = subparsers.add_parser("canvas", help="修改项目画布、标签和导出设置")
    canvas_parser.add_argument("--project", required=True)
    canvas_parser.add_argument("--output", required=True, help="新的 .figbox 输出")
    canvas_parser.add_argument("--canvas-width", type=float)
    canvas_parser.add_argument("--canvas-height", type=float)
    canvas_parser.add_argument("--margin", type=float)
    canvas_parser.add_argument("--spacing", type=float)
    canvas_parser.add_argument("--grid-size", type=float)
    canvas_parser.add_argument("--dpi", type=int)
    canvas_parser.add_argument("--label-fontsize", type=int)
    canvas_parser.add_argument("--label-color")
    canvas_parser.add_argument("--label-offset", type=float)
    label_visibility = canvas_parser.add_mutually_exclusive_group()
    label_visibility.add_argument("--show-labels", dest="label_visible", action="store_true")
    label_visibility.add_argument("--hide-labels", dest="label_visible", action="store_false")
    label_weight = canvas_parser.add_mutually_exclusive_group()
    label_weight.add_argument("--bold-labels", dest="label_bold", action="store_true")
    label_weight.add_argument("--regular-labels", dest="label_bold", action="store_false")
    crop_group = canvas_parser.add_mutually_exclusive_group()
    crop_group.add_argument("--auto-crop", dest="auto_crop", action="store_true")
    crop_group.add_argument("--preserve-canvas", dest="auto_crop", action="store_false")
    canvas_parser.set_defaults(label_visible=None, label_bold=None, auto_crop=None)
    canvas_parser.add_argument("--overwrite", action="store_true")
    canvas_parser.set_defaults(handler=handle_canvas)

    export_parser = subparsers.add_parser("export", help="从现有项目导出 PDF/PNG/TIF、预览和验证")
    export_parser.add_argument("--project", required=True)
    export_parser.add_argument("--output", required=True, help="独立输出目录")
    export_parser.add_argument("--name")
    export_parser.add_argument("--format", choices=("pdf", "png", "tif", "all"), default="pdf")
    export_parser.add_argument("--dpi", type=int)
    export_parser.add_argument("--preview-dpi", type=int, default=120)
    export_parser.add_argument("--padding", type=float, default=2.0)
    export_parser.add_argument("--crop", choices=("project", "auto", "preserve"), default="project")
    export_parser.add_argument("--overwrite", action="store_true")
    export_parser.set_defaults(handler=handle_export)

    preferences_parser = subparsers.add_parser("preferences", help="查看或修改 V20 GUI 持久化默认设置")
    preferences_parser.add_argument("--set", action="append", help="key=value，可重复")
    preferences_parser.set_defaults(handler=handle_preferences)
    return parser


def main(argv=None):
    configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        paths = args.handler(args)
    except Exception as error:
        if LOGGER.handlers:
            LOGGER.exception("运行失败: %s", error)
            close_logging()
        else:
            print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(json.dumps(paths, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
