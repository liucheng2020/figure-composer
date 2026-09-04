"""V20 CLI 的项目读取、布局和编辑操作。"""

import json
import math
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz

import project_io
from layout_engine import LayoutEngine, LayoutItem
from pdf_boundary_fix import expand_pdf_bounds_directional, shrink_pdf_bounds_directional
from pdf_utils import PDFInfo, parse_filename


@dataclass
class LoadedProject:
    """已展开且可编辑的 FigBox 项目。"""

    source_path: Path
    data: dict
    layouts: list
    temp_dir: str

    @classmethod
    def open(cls, path):
        source_path = Path(path).resolve()
        if source_path.suffix.lower() == ".figbox":
            data, temp_dir = project_io.unpack_figbox(str(source_path))
        elif source_path.suffix.lower() == ".figproj":
            data, temp_dir = project_io.import_legacy_figproj(str(source_path))
        else:
            raise ValueError("项目文件必须是 .figbox 或 .figproj")
        return cls(source_path, data, layouts_from_project_data(data), temp_dir)

    def close(self):
        if self.temp_dir:
            project_io.cleanup_temp_dir(self.temp_dir)
            self.temp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def layouts_from_project_data(project_data):
    """把项目 JSON 还原为 LayoutItem。"""
    layouts = []
    for index, record in enumerate(project_data.get("layouts", [])):
        pdf_path = record.get("pdf_path")
        if not pdf_path or not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"项目素材不存在: {pdf_path}")
        with fitz.open(pdf_path) as document:
            if len(document) == 0:
                raise ValueError(f"PDF 没有页面: {pdf_path}")
            rect = document[0].rect
        original_path = record.get("original_path") or pdf_path
        filename = os.path.basename(original_path) or os.path.basename(pdf_path)
        pdf_info = PDFInfo(
            filepath=pdf_path,
            filename=filename,
            width=rect.width,
            height=rect.height,
            aspect_ratio=rect.width / rect.height if rect.height else 1.0,
            sort_key=parse_filename(filename),
            expand_boundary=record.get("expand_boundary", False),
            expanded_filepath=record.get("expanded_filepath"),
            cumulative_margin=record.get("cumulative_margin", 0),
            original_path=original_path,
            provenance=record.get("provenance"),
        )
        pdf_info.source_filename = filename
        pdf_info.source_page = record.get("source_page", 1)
        pdf_info.source_page_count = record.get("source_page_count", 1)
        layouts.append(LayoutItem(
            pdf_info=pdf_info,
            x=float(record.get("x", 0)),
            y=float(record.get("y", 0)),
            width=float(record.get("width", 100)),
            height=float(record.get("height", 100)),
            rotation=float(record.get("rotation", 0)),
            label=str(record.get("label", panel_label(index))),
        ))
    if not layouts:
        raise ValueError("项目没有布局数据")
    return layouts


def panel_label(index):
    """生成 Excel 风格 panel 标签。"""
    value = index + 1
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(65 + remainder) + label
    return label


def label_rank(label):
    """把 A、B、AA 等标签转换为稳定排序键。"""
    text = str(label).strip().upper()
    if not text or any(not ("A" <= char <= "Z") for char in text):
        return (1, text)
    value = 0
    for char in text:
        value = value * 26 + ord(char) - 64
    return (0, value)


def layout_record(layout):
    """把 LayoutItem 转为项目记录。"""
    return {
        "pdf_path": layout.pdf_info.filepath,
        "original_path": layout.pdf_info.original_path or layout.pdf_info.filepath,
        "x": layout.x,
        "y": layout.y,
        "width": layout.width,
        "height": layout.height,
        "rotation": layout.rotation,
        "label": layout.label,
        "expand_boundary": layout.pdf_info.expand_boundary,
        "expanded_filepath": layout.pdf_info.expanded_filepath,
        "cumulative_margin": layout.pdf_info.cumulative_margin,
        "provenance": layout.pdf_info.provenance,
        "source_page": getattr(layout.pdf_info, "source_page", 1),
        "source_page_count": getattr(layout.pdf_info, "source_page_count", 1),
    }


def move_existing_to_trash(path, overwrite):
    """保护已有结果；显式覆盖时移动到同级 .Trash。"""
    path = Path(path)
    if not path.exists():
        return
    if not overwrite:
        raise FileExistsError(f"输出已存在；如需重跑请使用 --overwrite: {path}")
    trash_dir = path.parent / ".Trash"
    trash_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(str(path), str(trash_dir / f"{path.stem}_{stamp}{path.suffix}"))


def save_project(session, output_path, overwrite=False):
    """把当前项目状态保存为自包含 V20 FigBox。"""
    output_path = Path(output_path).resolve()
    if output_path.suffix.lower() != ".figbox":
        raise ValueError("编辑后的项目必须保存为 .figbox")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    move_existing_to_trash(output_path, overwrite)

    data = dict(session.data)
    data["version"] = "20.0"
    data["canvas_width"] = float(data.get("canvas_width", 297))
    data["canvas_height"] = float(data.get("canvas_height", 210))
    data["layouts"] = [layout_record(layout) for layout in session.layouts]
    project_io.pack_figbox(str(output_path), data)
    return output_path


def parse_selector(layouts, selector):
    """解析 all、A,B,C 或 A-D 形式的 panel 选择器。"""
    if not selector or selector.strip().lower() == "all":
        return list(range(len(layouts)))
    labels = []
    for token in selector.split(","):
        token = token.strip().upper()
        if not token:
            continue
        if "-" in token:
            start, end = [part.strip() for part in token.split("-", 1)]
            start_rank = label_rank(start)
            end_rank = label_rank(end)
            if start_rank[0] or end_rank[0] or start_rank[1] > end_rank[1]:
                raise ValueError(f"无效 panel 范围: {token}")
            labels.extend(panel_label(index - 1) for index in range(start_rank[1], end_rank[1] + 1))
        else:
            labels.append(token)
    lookup = {str(layout.label).upper(): index for index, layout in enumerate(layouts)}
    missing = [label for label in labels if label not in lookup]
    if missing:
        raise ValueError(f"项目中不存在 panel: {missing}")
    indices = [lookup[label] for label in labels]
    if len(indices) != len(set(indices)):
        raise ValueError("panel 选择器包含重复项")
    return indices


def smart_relayout(layouts, selected_indices, layout_spec, fill_mode,
                   canvas_width, canvas_height, margin, spacing,
                   span_left=None, span_width=None, top_y=None):
    """执行 GUI 智能网格的三种布局行为。"""
    ordered_indices = sorted(selected_indices, key=lambda index: label_rank(layouts[index].label))
    selected = [layouts[index] for index in ordered_indices]
    if not selected:
        raise ValueError("没有选中 panel")

    engine = LayoutEngine(canvas_width, canvas_height, margin_mm=margin, spacing_mm=spacing)
    explicit_left = span_left is not None
    explicit_top = top_y is not None
    span_left = margin if span_left is None else span_left
    span_width = canvas_width - 2 * margin if span_width is None else span_width
    top_y = margin if top_y is None else top_y

    if fill_mode == "no-scale":
        if layout_spec.kind != "grid":
            raise ValueError("仅摆放不缩放只适用于规则网格")
        rows = len(layout_spec.counts)
        columns = max(layout_spec.counts)
        max_width = max(item.width for item in selected)
        max_height = max(item.height for item in selected)
        total_width = columns * max_width + (columns - 1) * spacing
        total_height = rows * max_height + (rows - 1) * spacing
        start_x = span_left if explicit_left else max(margin, (canvas_width - total_width) / 2)
        start_y = top_y if explicit_top else max(margin, (canvas_height - total_height) / 2)
        new_layouts = []
        cursor = 0
        for row_index, count in enumerate(layout_spec.counts):
            for column_index in range(count):
                item = selected[cursor]
                cursor += 1
                new_layouts.append(LayoutItem(
                    item.pdf_info,
                    start_x + column_index * (max_width + spacing),
                    start_y + row_index * (max_height + spacing),
                    item.width,
                    item.height,
                    item.rotation,
                    item.label,
                ))
    elif layout_spec.kind == "columns":
        if fill_mode != "equal-height":
            raise ValueError("非对称列模板仅支持 equal-height")
        new_layouts = engine.asymmetric_columns(
            selected, list(layout_spec.counts), span_left, top_y, span_width, spacing)
    elif fill_mode == "equal-height":
        new_layouts = engine.asymmetric_rows(
            selected, list(layout_spec.counts), span_left, top_y, span_width, spacing)
    elif fill_mode == "uniform-scale":
        if layout_spec.kind != "grid":
            raise ValueError("统一比例填充只适用于规则网格")
        new_layouts = []
        cursor = 0
        current_y = top_y
        for count in layout_spec.counts:
            row_items = selected[cursor:cursor + count]
            cursor += count
            _, sizes = engine.uniform_fill(
                [(item.width, item.height) for item in row_items], span_width, spacing)
            current_x = span_left
            row_height = 0.0
            for item, (width, height) in zip(row_items, sizes):
                new_layouts.append(LayoutItem(
                    item.pdf_info, current_x, current_y, width, height,
                    item.rotation, item.label))
                current_x += width + spacing
                row_height = max(row_height, height)
            current_y += row_height + spacing
    else:
        raise ValueError(f"未知填充模式: {fill_mode}")

    for index, new_layout in zip(ordered_indices, new_layouts):
        layouts[index] = new_layout
    return layouts


def renumber_layouts(layouts):
    """按当前列表顺序把标签重编号为连续序列。"""
    for index, layout in enumerate(layouts):
        layout.label = panel_label(index)


def apply_transform(layouts, selected_indices, operation, **values):
    """执行 GUI 中会改变 panel 几何或顺序的编辑动作。"""
    selected = [layouts[index] for index in selected_indices]
    if not selected:
        raise ValueError("没有选中 panel")

    if operation == "scale":
        factor = float(values["factor"])
        if factor <= 0:
            raise ValueError("缩放因子必须大于 0")
        for item in selected:
            item.width *= factor
            item.height = item.width / item.pdf_info.aspect_ratio
    elif operation == "same-width":
        reference = max(item.width for item in selected)
        for item in selected:
            item.width = reference
            item.height = reference / item.pdf_info.aspect_ratio
    elif operation == "same-height":
        reference = max(item.height for item in selected)
        for item in selected:
            item.height = reference
            item.width = reference * item.pdf_info.aspect_ratio
    elif operation == "align-left":
        anchor = min(item.x for item in selected)
        for item in selected:
            item.x = anchor
    elif operation == "align-right":
        anchor = max(item.x + item.width for item in selected)
        for item in selected:
            item.x = anchor - item.width
    elif operation == "align-top":
        anchor = min(item.y for item in selected)
        for item in selected:
            item.y = anchor
    elif operation == "align-bottom":
        anchor = max(item.y + item.height for item in selected)
        for item in selected:
            item.y = anchor - item.height
    elif operation == "align-h-center":
        anchor = sum(item.x + item.width / 2 for item in selected) / len(selected)
        for item in selected:
            item.x = anchor - item.width / 2
    elif operation == "align-v-center":
        anchor = sum(item.y + item.height / 2 for item in selected) / len(selected)
        for item in selected:
            item.y = anchor - item.height / 2
    elif operation == "distribute-horizontal":
        ordered = sorted(selected, key=lambda item: item.x)
        if len(ordered) < 3:
            raise ValueError("均分至少需要 3 个 panel")
        step = (ordered[-1].x - ordered[0].x) / (len(ordered) - 1)
        for index, item in enumerate(ordered):
            item.x = ordered[0].x + index * step
    elif operation == "distribute-vertical":
        ordered = sorted(selected, key=lambda item: item.y)
        if len(ordered) < 3:
            raise ValueError("均分至少需要 3 个 panel")
        step = (ordered[-1].y - ordered[0].y) / (len(ordered) - 1)
        for index, item in enumerate(ordered):
            item.y = ordered[0].y + index * step
    elif operation == "spacing-horizontal":
        spacing = float(values["value"])
        ordered = sorted(selected, key=lambda item: item.x)
        cursor = ordered[0].x + ordered[0].width
        for item in ordered[1:]:
            item.x = cursor + spacing
            cursor = item.x + item.width
    elif operation == "spacing-vertical":
        spacing = float(values["value"])
        ordered = sorted(selected, key=lambda item: item.y)
        cursor = ordered[0].y + ordered[0].height
        for item in ordered[1:]:
            item.y = cursor + spacing
            cursor = item.y + item.height
    elif operation == "rotate":
        angle = float(values["angle"])
        absolute = bool(values.get("absolute"))
        for item in selected:
            item.rotation = angle % 360 if absolute else (item.rotation + angle) % 360
    elif operation == "move":
        for item in selected:
            if values.get("x") is not None:
                item.x = float(values["x"])
            else:
                item.x += float(values.get("dx") or 0)
            if values.get("y") is not None:
                item.y = float(values["y"])
            else:
                item.y += float(values.get("dy") or 0)
    elif operation == "resize":
        width = values.get("width")
        height = values.get("height")
        if width is None and height is None:
            raise ValueError("resize 至少需要 --width 或 --height")
        for item in selected:
            if width is not None and height is not None:
                item.width = float(width)
                item.height = float(height)
            elif width is not None:
                item.width = float(width)
                item.height = item.width / item.pdf_info.aspect_ratio
            else:
                item.height = float(height)
                item.width = item.height * item.pdf_info.aspect_ratio
    elif operation == "delete":
        if len(selected_indices) == len(layouts):
            raise ValueError("不能删除项目中的全部 panel")
        selected_set = set(selected_indices)
        layouts[:] = [item for index, item in enumerate(layouts) if index not in selected_set]
        renumber_layouts(layouts)
    elif operation == "relabel":
        if len(selected_indices) != 1:
            raise ValueError("标签级联一次只能选择 1 个 panel")
        if not values.get("new_label"):
            raise ValueError("relabel 需要 --new-label")
        new_label = str(values["new_label"]).upper()
        target_rank = label_rank(new_label)
        if target_rank[0] or target_rank[1] < 1:
            raise ValueError(f"无效目标标签: {new_label}")
        ordered = sorted(layouts, key=lambda item: label_rank(item.label))
        moved = layouts[selected_indices[0]]
        ordered.remove(moved)
        insert_index = min(target_rank[1] - 1, len(ordered))
        ordered.insert(insert_index, moved)
        layouts[:] = ordered
        renumber_layouts(layouts)
    else:
        raise ValueError(f"未知编辑操作: {operation}")
    return layouts


def apply_boundary(layouts, selected_indices, operation, points, directions, temp_dir):
    """扩展、紧缩或恢复所选 PDF 边界。"""
    if operation != "restore" and points <= 0:
        raise ValueError("边界点数必须大于 0")
    direction_set = {direction.strip().lower() for direction in directions.split(",") if direction.strip()}
    valid = {"left", "right", "top", "bottom"}
    if operation != "restore" and (not direction_set or not direction_set <= valid):
        raise ValueError("directions 只能包含 left,right,top,bottom")
    flags = {direction: direction in direction_set for direction in valid}

    for index in selected_indices:
        item = layouts[index]
        if operation == "restore":
            item.pdf_info.expand_boundary = False
            item.pdf_info.expanded_filepath = None
            item.pdf_info.cumulative_margin = 0
            continue
        output_path = Path(temp_dir) / f"boundary_{item.label}_{operation}.pdf"
        if operation == "expand":
            expanded = expand_pdf_bounds_directional(
                item.pdf_info.filepath,
                str(output_path),
                margin=points,
                expand_left=flags["left"],
                expand_right=flags["right"],
                expand_top=flags["top"],
                expand_bottom=flags["bottom"],
            )
            item.pdf_info.cumulative_margin = points
        elif operation == "shrink":
            expanded = shrink_pdf_bounds_directional(
                item.pdf_info.filepath,
                str(output_path),
                shrink_amount=points,
                shrink_left=flags["left"],
                shrink_right=flags["right"],
                shrink_top=flags["top"],
                shrink_bottom=flags["bottom"],
            )
            item.pdf_info.cumulative_margin = -points
        else:
            raise ValueError(f"未知边界操作: {operation}")
        item.pdf_info.expand_boundary = True
        item.pdf_info.expanded_filepath = expanded
    return layouts


def update_project_settings(session, **values):
    """更新画布和可导出的项目设置。"""
    if values.get("canvas_width") is not None:
        session.data["canvas_width"] = float(values["canvas_width"])
    if values.get("canvas_height") is not None:
        session.data["canvas_height"] = float(values["canvas_height"])
    settings = dict(session.data.get("settings", {}))
    for key in (
        "margin", "spacing", "grid_size", "dpi", "label_fontsize",
        "label_visible", "label_bold", "label_color", "label_offset", "auto_crop",
    ):
        if values.get(key) is not None:
            settings[key] = values[key]
    session.data["settings"] = settings
    return session


def inspect_project(session):
    """返回项目、画布、设置、素材和 panel 几何清单。"""
    return {
        "project": str(session.source_path),
        "version": session.data.get("version"),
        "canvas_name": session.data.get("canvas_name"),
        "canvas_width_mm": session.data.get("canvas_width"),
        "canvas_height_mm": session.data.get("canvas_height"),
        "settings": session.data.get("settings", {}),
        "panel_count": len(session.layouts),
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
                "boundary_modified": bool(item.pdf_info.expand_boundary),
                "boundary_points": item.pdf_info.cumulative_margin,
            }
            for item in session.layouts
        ],
    }
