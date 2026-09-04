"""图片排版算法引擎 - V20.

设计原则（第一性）：
    科研组图最花时间的是"反复缩放使一行图刚好铺满画布、且每张图保持自己原本
    的比例与相对大小"。不同图本来就不该被强行拉成等高。

    因此核心原语只有一个——"统一系数填满指定宽度"：
        给定若干图（各有自己的宽、高），乘以**同一个**缩放系数，使它们
        从左到右、以固定间距排列后，总宽度恰好等于一段指定的横向空间。
        于是它们彼此的相对大小被完整保留，高度各不相同。

    这个原语支撑"填充剩余宽度"功能：
        自动识别某一行里已经摆好的图占用的横向范围，把选中的图等比缩放后
        顺序填进该行右侧的剩余宽度，并与已有图顶部对齐。

    （V18 的 7 个旧自动排版、以及 V19 早期试验的"等高两端对齐"均已废弃。）
"""

import math
from typing import List, Tuple
from dataclasses import dataclass
from pdf_utils import PDFInfo


@dataclass
class LayoutItem:
    """布局中单张图片的位置与尺寸信息。"""
    pdf_info: PDFInfo
    x: float          # 位置（mm）
    y: float
    width: float      # 尺寸（mm）
    height: float
    rotation: float = 0.0   # 旋转角度（度）
    label: str = "A"        # 标签 A、B、C …


class LayoutEngine:
    """为多张图片计算排版几何。"""

    def __init__(self, canvas_width_mm: float, canvas_height_mm: float,
                 margin_mm: float = 5.0, spacing_mm: float = 5.0):
        """
        Args:
            canvas_width_mm: 画布宽度（mm）
            canvas_height_mm: 画布高度（mm）
            margin_mm: 画布四周页边距（mm）
            spacing_mm: 图片之间的固定间距（mm）
        """
        self.canvas_width = canvas_width_mm
        self.canvas_height = canvas_height_mm
        self.margin = margin_mm
        self.spacing = spacing_mm

        self.available_width = canvas_width_mm - 2 * margin_mm
        self.available_height = canvas_height_mm - 2 * margin_mm

    # ==================================================================
    # 核心原语：统一系数填满指定宽度
    # ==================================================================

    def uniform_fill(self, sizes: List[Tuple[float, float]],
                     span_width: float, gap: float) -> Tuple[float, List[Tuple[float, float]]]:
        """求统一缩放系数，使若干图排成一行后总宽恰好 = span_width。

        行宽 = Σ(w_i * s) + (k-1)*gap = span_width
              => s = (span_width - (k-1)*gap) / Σw_i

        Args:
            sizes: 各图当前的 (宽, 高)（mm），保留它们彼此的相对大小
            span_width: 要填满的横向空间宽度（mm）
            gap: 图片之间的固定间距（mm）

        Returns:
            (scale, [(w, h), ...])，scale 为统一系数，列表为缩放后的尺寸。
        """
        k = len(sizes)
        if k == 0:
            return 1.0, []
        total_w = sum(w for w, _ in sizes)
        if total_w <= 0:
            return 1.0, list(sizes)
        avail = span_width - (k - 1) * gap
        if avail <= 0:
            # 间距已超过可用宽度，退化处理：不缩放
            return 1.0, list(sizes)
        scale = avail / total_w
        return scale, [(w * scale, h * scale) for (w, h) in sizes]

    def justified_row(self, sizes: List, span_width: float, gap: float = None) -> List:
        """等高填充：把若干图缩放到【同一个高度】，以固定间距正好填满 span_width。

        给定每张图的 (宽, 高)，各图宽高比 a_i = 宽/高。要求它们等高 h、铺满宽度：
            Σ(a_i · h) + (k−1)·gap = span_width  ⇒  h = (span_width − (k−1)·gap) / Σa_i
        于是输出全部等高（h 相同），宽度按各自比例 a_i·h，总宽恰好 = span_width。
        等高的输入永远保持等高；不等高的输入会被统一拉到同一高度。

        返回 [(宽, 高), ...]，顺序与输入一致。
        """
        if gap is None:
            gap = self.spacing
        k = len(sizes)
        if k == 0:
            return []
        aspects = [(w / h if h > 0 else 1.0) for (w, h) in sizes]
        avail = span_width - (k - 1) * gap
        if avail <= 0:
            avail = span_width
        h = avail / sum(aspects)
        return [(a * h, h) for a in aspects]

    def grid_proportional(self, items: List, rows: int, cols: int) -> List[LayoutItem]:
        """智能网格：把图按 rows×cols 切成若干行，每行用统一系数等比缩放铺满画布宽度。

        - 从画布左页边距开始算，每行铺满 [左边距, 右边距] 的可用宽度（固定间距）。
        - 同一行内各图乘同一系数：保留彼此相对大小与各自宽高比，高度自然不同。
        - 行与行之间为固定间距；每行顶部对齐，整块从上页边距开始向下堆叠。
        - 末行不足 cols 张时，同样只按"该行实际张数"铺满整行宽度。

        items: 需带 .width/.height/.pdf_info/.label（即 LayoutItem 或兼容对象）。
        """
        n = len(items)
        if n == 0:
            return []

        out = []
        y = self.margin
        idx = 0
        for _ in range(rows):
            row_items = items[idx:idx + cols]
            idx += cols
            if not row_items:
                break
            sizes = [(it.width, it.height) for it in row_items]
            _, new_sizes = self.uniform_fill(sizes, self.available_width, self.spacing)
            x = self.margin
            row_h = 0.0
            for it, (w, h) in zip(row_items, new_sizes):
                out.append(LayoutItem(
                    pdf_info=it.pdf_info,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    rotation=getattr(it, 'rotation', 0.0),
                    label=it.label,
                ))
                x += w + self.spacing
                row_h = max(row_h, h)
            y += row_h + self.spacing

        return out

    @staticmethod
    def parse_column_pattern(pattern: str, expected_count: int = None) -> List[int]:
        """Parse an asymmetric column pattern such as ``2+1`` or ``1+2``.

        The numbers represent how many figures are stacked in each column.
        For example, ``2+1`` means two figures in the left column and one
        figure spanning the same total height in the right column.
        """
        if not isinstance(pattern, str):
            raise ValueError("模板必须是文本，例如 2+1")
        parts = [part.strip() for part in pattern.split("+")]
        if not parts or any(not part.isdigit() for part in parts):
            raise ValueError("模板只能包含数字和 +，例如 2+1")
        counts = [int(part) for part in parts]
        if any(count <= 0 for count in counts):
            raise ValueError("每一列至少需要 1 张图")
        if expected_count is not None and sum(counts) != expected_count:
            raise ValueError(f"模板需要 {sum(counts)} 张图，但当前选中了 {expected_count} 张")
        return counts

    def asymmetric_columns(self, items: List, column_counts: List[int],
                           span_left: float = None, top_y: float = None,
                           span_width: float = None, gap: float = None) -> List[LayoutItem]:
        """Lay out selected figures in stacked columns with equal total height.

        Each column receives a fixed number of figures. All columns are scaled
        so their total heights match, and the whole block fills ``span_width``.
        Figure aspect ratios are preserved.
        """
        if not items:
            return []
        if sum(column_counts) != len(items):
            raise ValueError("列模板数量与图片数量不一致")
        if gap is None:
            gap = self.spacing
        if span_left is None:
            span_left = self.margin
        if top_y is None:
            top_y = self.margin
        if span_width is None:
            span_width = self.available_width

        columns = []
        cursor = 0
        for count in column_counts:
            col_items = items[cursor:cursor + count]
            cursor += count
            aspects = []
            for item in col_items:
                height = getattr(item, "height", 0.0)
                width = getattr(item, "width", 0.0)
                aspects.append(width / height if height > 0 else 1.0)
            columns.append((col_items, aspects))

        # For a column with target height H and k stacked figures:
        # width = (H - (k - 1) * gap) / Σ(1 / aspect_i)
        # Sum all column widths plus inter-column gaps and solve H directly.
        denominators = [sum(1.0 / aspect for aspect in aspects) for _, aspects in columns]
        vertical_gap_terms = [(len(col_items) - 1) * gap for col_items, _ in columns]
        horizontal_gaps = (len(columns) - 1) * gap
        denominator_sum = sum(1.0 / denom for denom in denominators if denom > 0)
        if denominator_sum <= 0:
            return []
        numerator = span_width - horizontal_gaps
        numerator += sum(vgap / denom for vgap, denom in zip(vertical_gap_terms, denominators) if denom > 0)
        target_height = numerator / denominator_sum
        min_height = max(vertical_gap_terms or [0.0]) + 1.0
        target_height = max(target_height, min_height)

        out = []
        x = span_left
        for (col_items, aspects), denom, vgap in zip(columns, denominators, vertical_gap_terms):
            col_width = (target_height - vgap) / denom if denom > 0 else 0.0
            y = top_y
            for item, aspect in zip(col_items, aspects):
                item_height = col_width / aspect if aspect > 0 else target_height
                out.append(LayoutItem(
                    pdf_info=item.pdf_info,
                    x=x,
                    y=y,
                    width=col_width,
                    height=item_height,
                    rotation=getattr(item, "rotation", 0.0),
                    label=item.label,
                ))
                y += item_height + gap
            x += col_width + gap

        return out

    def asymmetric_rows(self, items: List, row_counts: List[int],
                        span_left: float = None, top_y: float = None,
                        span_width: float = None, gap: float = None) -> List[LayoutItem]:
        """Lay out selected figures in stacked rows that each fill the same width.

        A pattern such as ``2+1`` means two figures on the top row and one
        figure on the bottom row. Each row is independently equal-height
        justified to the same target width.
        """
        if not items:
            return []
        if sum(row_counts) != len(items):
            raise ValueError("行模板数量与图片数量不一致")
        if gap is None:
            gap = self.spacing
        if span_left is None:
            span_left = self.margin
        if top_y is None:
            top_y = self.margin
        if span_width is None:
            span_width = self.available_width

        out = []
        cursor = 0
        y = top_y
        for count in row_counts:
            row_items = items[cursor:cursor + count]
            cursor += count
            sizes = [(item.width, item.height) for item in row_items]
            new_sizes = self.justified_row(sizes, span_width, gap)
            x = span_left
            row_height = 0.0
            for item, (width, height) in zip(row_items, new_sizes):
                out.append(LayoutItem(
                    pdf_info=item.pdf_info,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    rotation=getattr(item, "rotation", 0.0),
                    label=item.label,
                ))
                x += width + gap
                row_height = max(row_height, height)
            y += row_height + gap

        return out

    # ==================================================================
    # 导入后的初始铺排（仅为整理，非最终排版）
    # ==================================================================

    def flow_import(self, pdf_files: List[PDFInfo]) -> List[LayoutItem]:
        """导入后的初始铺排：全局统一缩放后按宽度换行、每行顶部对齐。

        采用单一全局系数缩放（保留所有图彼此的相对大小），不强行等高/等宽，
        只是把图整齐地铺开供用户后续用"填充剩余宽度"精修。
        """
        n = len(pdf_files)
        if n == 0:
            return []

        # 每行大致放几张（接近正方形排布）
        cols = max(1, math.ceil(math.sqrt(n)))
        cell_w = (self.available_width - (cols - 1) * self.spacing) / cols

        # 全局系数：让"最宽的图"恰好放进一个格子宽度（其余图按同一系数缩小，保留相对大小）
        max_w_pts = max(p.width for p in pdf_files)
        global_scale = cell_w / max_w_pts if max_w_pts > 0 else 1.0

        layouts = []
        x = self.margin
        y = self.margin
        row_max_h = 0.0
        right_limit = self.margin + self.available_width

        for idx, pdf in enumerate(pdf_files):
            w = pdf.width * global_scale
            h = pdf.height * global_scale

            # 需要换行：当前行已有图且再放会超出右边界
            if x > self.margin and (x + w) > right_limit + 1e-6:
                x = self.margin
                y += row_max_h + self.spacing
                row_max_h = 0.0

            layouts.append(LayoutItem(
                pdf_info=pdf,
                x=x,
                y=y,
                width=w,
                height=h,
                label=chr(65 + idx),
            ))
            x += w + self.spacing
            row_max_h = max(row_max_h, h)

        return layouts

    # ==================================================================
    # 单图与利用率（保留，供 GUI 其它处复用）
    # ==================================================================

    def _place_single_figure(self, pdf: PDFInfo) -> List[LayoutItem]:
        """单张图：居中并尽量放大。"""
        scale = min(self.available_width / pdf.width,
                    self.available_height / pdf.height)
        fig_width = pdf.width * scale
        fig_height = pdf.height * scale
        x = self.margin + (self.available_width - fig_width) / 2
        y = self.margin + (self.available_height - fig_height) / 2
        return [LayoutItem(
            pdf_info=pdf,
            x=x,
            y=y,
            width=fig_width,
            height=fig_height,
            label='A',
        )]

    def calculate_space_utilization(self, layouts: List[LayoutItem]) -> float:
        """计算图片占画布面积的百分比（0-100）。"""
        if not layouts:
            return 0.0
        total_figure_area = sum(item.width * item.height for item in layouts)
        canvas_area = self.canvas_width * self.canvas_height
        return (total_figure_area / canvas_area) * 100 if canvas_area > 0 else 0.0
