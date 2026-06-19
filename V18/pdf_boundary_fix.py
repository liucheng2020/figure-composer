"""
PDF边界扩展模块 - V8 Enhanced版本

V8修复：
- 修复CropBox not in MediaBox错误
- 确保CropBox始终在MediaBox范围内
- 增强错误处理和验证

策略：
1. 检测并移除页面大小的白色矩形蒙版
2. 扩展页面边界以包含所有内容
3. 确保CropBox和MediaBox的正确关系
4. 保持矢量质量
"""

import fitz
import os
import tempfile
import re


def get_content_bbox(page):
    """
    获取页面实际内容的边界框
    排除页面大小的白色矩形（裁剪框）
    """
    drawings = page.get_drawings()
    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])

    page_rect = page.rect
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    # 检查绘图对象，排除页面大小的白色矩形
    for drawing in drawings:
        rect = drawing.get("rect")
        if not rect:
            continue

        # 跳过页面大小的矩形（裁剪框）
        is_page_rect = (
            abs(rect.x0 - page_rect.x0) < 1 and
            abs(rect.y0 - page_rect.y0) < 1 and
            abs(rect.x1 - page_rect.x1) < 1 and
            abs(rect.y1 - page_rect.y1) < 1
        )

        if is_page_rect:
            fill = drawing.get("fill")
            # 如果是白色填充，跳过
            if fill and fill[0] > 0.9 and fill[1] > 0.9 and fill[2] > 0.9:
                continue

        min_x = min(min_x, rect.x0)
        min_y = min(min_y, rect.y0)
        max_x = max(max_x, rect.x1)
        max_y = max(max_y, rect.y1)

    # 检查文本
    for block in blocks:
        if "bbox" in block:
            bbox = block["bbox"]
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

    if min_x == float('inf'):
        return page.rect

    return fitz.Rect(min_x, min_y, max_x, max_y)


def expand_pdf_bounds(input_path, output_path=None, margin=10):
    """
    扩展PDF边界以显示被裁剪的内容 - V8增强版

    V8修复：
    - 确保MediaBox和CropBox的正确关系
    - 验证边界框的有效性
    - 增强错误处理

    Args:
        input_path: 输入PDF路径
        output_path: 输出PDF路径（如果为None，创建临时文件）
        margin: 扩展边距（points）

    Returns:
        str: 输出文件路径
    """
    doc = fitz.open(input_path)
    page = doc[0]

    page_rect = page.rect

    # 获取真实内容边界（排除裁剪框）
    content_bbox = get_content_bbox(page)

    # 计算新页面大小 - V8修复：允许负坐标以正确处理边界扩展
    new_x0 = min(page_rect.x0, content_bbox.x0) - margin
    new_y0 = min(page_rect.y0, content_bbox.y0) - margin
    new_x1 = max(page_rect.x1, content_bbox.x1) + margin
    new_y1 = max(page_rect.y1, content_bbox.y1) + margin

    new_width = new_x1 - new_x0
    new_height = new_y1 - new_y0

    # V8 FIX: 验证尺寸合理性（但允许负起始坐标）
    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"无效的页面尺寸: {new_width}x{new_height}")

    if new_width > 100000 or new_height > 100000:
        raise ValueError(f"页面尺寸过大: {new_width}x{new_height}，可能存在错误")

    # 计算偏移量
    offset_x = -new_x0
    offset_y = -new_y0

    # V9 FIX: 首先设置MediaBox
    new_mediabox = fitz.Rect(0, 0, new_width, new_height)
    page.set_mediabox(new_mediabox)

    # V9 FIX: 然后设置CropBox为MediaBox（确保cropbox在mediabox内）
    # 使用page.mediabox来获取刚设置的MediaBox，确保完全一致
    page.set_cropbox(page.mediabox)

    # 应用坐标变换
    try:
        xref = page.get_contents()
        if isinstance(xref, list):
            xref = xref[0]

        stream = doc.xref_stream(xref)

        # 在内容前添加变换矩阵
        transform_cmd = f"q\n1 0 0 1 {offset_x} {offset_y} cm\n".encode('latin-1')
        new_stream = transform_cmd + stream + b"\nQ"

        doc.update_stream(xref, new_stream)

    except Exception as e:
        print(f"应用变换时出错: {e}")
        # V8: 即使变换失败，也继续保存（可能仍然有用）

    # 保存
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

    try:
        # V8 FIX: 使用更温和的保存选项
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    except Exception as e:
        # V8: 如果保存失败，尝试不使用clean选项
        try:
            doc.save(output_path, garbage=4, deflate=True)
        except Exception as e2:
            raise RuntimeError(f"保存PDF失败: {e2}") from e

    doc.close()

    return output_path


def get_expansion_info(pdf_path):
    """获取PDF边界扩展信息"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        content_bbox = get_content_bbox(page)
        page_rect = page.rect

        info = {
            'original_rect': page_rect,
            'content_bbox': content_bbox,
            'needs_expansion': (
                content_bbox.x0 < page_rect.x0 or
                content_bbox.y0 < page_rect.y0 or
                content_bbox.x1 > page_rect.x1 or
                content_bbox.y1 > page_rect.y1
            ),
            'overflow_left': max(0, page_rect.x0 - content_bbox.x0),
            'overflow_top': max(0, page_rect.y0 - content_bbox.y0),
            'overflow_right': max(0, content_bbox.x1 - page_rect.x1),
            'overflow_bottom': max(0, content_bbox.y1 - page_rect.y1),
        }

        doc.close()
        return info

    except Exception as e:
        print(f"获取PDF边界信息失败: {e}")
        return None


def needs_boundary_expansion(pdf_path, threshold=5):
    """检测PDF是否需要边界扩展"""
    info = get_expansion_info(pdf_path)
    if not info:
        return False

    return info['needs_expansion']


def expand_pdf_bounds_directional(input_path, output_path=None, margin=10,
                                  expand_left=True, expand_right=True,
                                  expand_top=True, expand_bottom=True):
    """
    按指定方向扩展PDF边界 - V8 NEW

    Args:
        input_path: 输入PDF路径
        output_path: 输出PDF路径（如果为None，创建临时文件）
        margin: 扩展边距（points）
        expand_left: 是否向左扩展
        expand_right: 是否向右扩展
        expand_top: 是否向上扩展
        expand_bottom: 是否向下扩展

    Returns:
        str: 输出文件路径
    """
    doc = fitz.open(input_path)
    page = doc[0]

    page_rect = page.rect

    # 获取真实内容边界（排除裁剪框）
    content_bbox = get_content_bbox(page)

    # 根据方向选择计算新页面大小
    if expand_left:
        new_x0 = min(page_rect.x0, content_bbox.x0) - margin
    else:
        new_x0 = page_rect.x0

    if expand_top:
        new_y0 = min(page_rect.y0, content_bbox.y0) - margin
    else:
        new_y0 = page_rect.y0

    if expand_right:
        new_x1 = max(page_rect.x1, content_bbox.x1) + margin
    else:
        new_x1 = page_rect.x1

    if expand_bottom:
        new_y1 = max(page_rect.y1, content_bbox.y1) + margin
    else:
        new_y1 = page_rect.y1

    new_width = new_x1 - new_x0
    new_height = new_y1 - new_y0

    # 验证尺寸合理性
    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"无效的页面尺寸: {new_width}x{new_height}")

    if new_width > 100000 or new_height > 100000:
        raise ValueError(f"页面尺寸过大: {new_width}x{new_height}，可能存在错误")

    # 计算偏移量
    offset_x = -new_x0
    offset_y = -new_y0

    # V9 FIX: 首先设置MediaBox
    new_mediabox = fitz.Rect(0, 0, new_width, new_height)
    page.set_mediabox(new_mediabox)

    # V9 FIX: 然后设置CropBox为MediaBox（确保cropbox在mediabox内）
    page.set_cropbox(page.mediabox)

    # 应用坐标变换
    try:
        xref = page.get_contents()
        if isinstance(xref, list):
            xref = xref[0]

        stream = doc.xref_stream(xref)

        # 在内容前添加变换矩阵
        transform_cmd = f"q\n1 0 0 1 {offset_x} {offset_y} cm\n".encode('latin-1')
        new_stream = transform_cmd + stream + b"\nQ"

        doc.update_stream(xref, new_stream)

    except Exception as e:
        print(f"应用变换时出错: {e}")

    # 保存
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

    try:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    except Exception as e:
        try:
            doc.save(output_path, garbage=4, deflate=True)
        except Exception as e2:
            raise RuntimeError(f"保存PDF失败: {e2}") from e

    doc.close()

    return output_path


def shrink_pdf_bounds(input_path, output_path=None, margin=0):
    """
    紧缩PDF边界以移除空白区域 - V9 NEW (修复cropbox错误)

    将PDF裁剪到实际内容区域，移除周围的空白。

    Args:
        input_path: 输入PDF路径
        output_path: 输出PDF路径（如果为None，创建临时文件）
        margin: 保留的边距（points），默认为0

    Returns:
        str: 输出文件路径
    """
    doc = fitz.open(input_path)
    page = doc[0]

    page_rect = page.rect

    # 获取真实内容边界
    content_bbox = get_content_bbox(page)

    # 添加边距，确保不超出原始页面边界
    new_x0 = max(page_rect.x0, content_bbox.x0 - margin)
    new_y0 = max(page_rect.y0, content_bbox.y0 - margin)
    new_x1 = min(page_rect.x1, content_bbox.x1 + margin)
    new_y1 = min(page_rect.y1, content_bbox.y1 + margin)

    new_width = new_x1 - new_x0
    new_height = new_y1 - new_y0

    # 验证尺寸合理性
    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"无效的页面尺寸: {new_width}x{new_height}")

    # 计算偏移量
    offset_x = -new_x0
    offset_y = -new_y0

    # 创建新文档
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=new_width, height=new_height)

    # 使用show_pdf_page复制内容，设置正确的矩阵变换
    # 创建变换矩阵：先平移offset，使内容对齐到新页面的(0,0)
    src_rect = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
    dest_rect = fitz.Rect(0, 0, new_width, new_height)

    # 直接显示裁剪区域的内容
    new_page.show_pdf_page(dest_rect, doc, 0, clip=src_rect)

    # 保存
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

    try:
        new_doc.save(output_path, garbage=4, deflate=True, clean=True)
    except Exception as e:
        try:
            new_doc.save(output_path, garbage=4, deflate=True)
        except Exception as e2:
            raise RuntimeError(f"保存PDF失败: {e2}") from e

    doc.close()
    new_doc.close()

    return output_path


def shrink_pdf_bounds_directional(input_path, output_path=None, shrink_amount=0,
                                   shrink_left=True, shrink_right=True,
                                   shrink_top=True, shrink_bottom=True):
    """
    按指定方向紧缩PDF边界 - V9 NEW

    Args:
        input_path: 输入PDF路径
        output_path: 输出PDF路径（如果为None，创建临时文件）
        shrink_amount: 紧缩量（points），从边界向内裁剪的距离
        shrink_left: 是否从左侧紧缩
        shrink_right: 是否从右侧紧缩
        shrink_top: 是否从顶部紧缩
        shrink_bottom: 是否从底部紧缩

    Returns:
        str: 输出文件路径
    """
    doc = fitz.open(input_path)
    page = doc[0]

    page_rect = page.rect

    # 获取真实内容边界
    content_bbox = get_content_bbox(page)

    # 根据方向计算新的边界
    if shrink_left:
        new_x0 = max(page_rect.x0, content_bbox.x0 + shrink_amount)
    else:
        new_x0 = page_rect.x0

    if shrink_top:
        new_y0 = max(page_rect.y0, content_bbox.y0 + shrink_amount)
    else:
        new_y0 = page_rect.y0

    if shrink_right:
        new_x1 = min(page_rect.x1, content_bbox.x1 - shrink_amount)
    else:
        new_x1 = page_rect.x1

    if shrink_bottom:
        new_y1 = min(page_rect.y1, content_bbox.y1 - shrink_amount)
    else:
        new_y1 = page_rect.y1

    # 确保裁剪后的区域有效
    new_x0 = min(new_x0, new_x1 - 10)  # 至少保留10点宽度
    new_y0 = min(new_y0, new_y1 - 10)  # 至少保留10点高度

    new_width = new_x1 - new_x0
    new_height = new_y1 - new_y0

    # 验证尺寸合理性
    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"无效的页面尺寸: {new_width}x{new_height}")

    # 创建新文档
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=new_width, height=new_height)

    # 复制内容
    src_rect = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
    dest_rect = fitz.Rect(0, 0, new_width, new_height)

    new_page.show_pdf_page(dest_rect, doc, 0, clip=src_rect)

    # 保存
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)

    try:
        new_doc.save(output_path, garbage=4, deflate=True, clean=True)
    except Exception as e:
        try:
            new_doc.save(output_path, garbage=4, deflate=True)
        except Exception as e2:
            raise RuntimeError(f"保存PDF失败: {e2}") from e

    doc.close()
    new_doc.close()

    return output_path


def get_whitespace_info(pdf_path):
    """获取PDF空白区域信息 - V9 NEW"""
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        content_bbox = get_content_bbox(page)
        page_rect = page.rect

        info = {
            'page_rect': page_rect,
            'content_bbox': content_bbox,
            'has_whitespace': (
                content_bbox.x0 > page_rect.x0 or
                content_bbox.y0 > page_rect.y0 or
                content_bbox.x1 < page_rect.x1 or
                content_bbox.y1 < page_rect.y1
            ),
            'whitespace_left': content_bbox.x0 - page_rect.x0,
            'whitespace_top': content_bbox.y0 - page_rect.y0,
            'whitespace_right': page_rect.x1 - content_bbox.x1,
            'whitespace_bottom': page_rect.y1 - content_bbox.y1,
            'content_width': content_bbox.width,
            'content_height': content_bbox.height,
            'page_width': page_rect.width,
            'page_height': page_rect.height,
        }

        doc.close()
        return info

    except Exception as e:
        print(f"获取PDF空白信息失败: {e}")
        return None


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        margin = 30 if len(sys.argv) < 3 else int(sys.argv[2])

        print("=" * 70)
        print("PDF边界扩展工具")
        print("=" * 70)

        # 显示信息
        info = get_expansion_info(pdf_path)
        if info:
            print(f"\n原始页面: {info['original_rect']}")
            print(f"内容边界: {info['content_bbox']}")
            print(f"需要扩展: {info['needs_expansion']}")

            if info['needs_expansion']:
                print(f"\n溢出情况:")
                if info['overflow_left'] > 0:
                    print(f"  左侧: {info['overflow_left']:.2f} points")
                if info['overflow_top'] > 0:
                    print(f"  顶部: {info['overflow_top']:.2f} points")
                if info['overflow_right'] > 0:
                    print(f"  右侧: {info['overflow_right']:.2f} points")
                if info['overflow_bottom'] > 0:
                    print(f"  底部: {info['overflow_bottom']:.2f} points")

        # 扩展
        print(f"\n正在扩展边界 (margin={margin} points)...")
        output = expand_pdf_bounds(
            pdf_path,
            pdf_path.replace('.pdf', '_expanded.pdf'),
            margin=margin
        )

        print(f"\n✅ 完成！")
        print(f"输出: {output}")

        # 验证
        info2 = get_expansion_info(output)
        if info2:
            print(f"\n扩展后页面: {info2['original_rect']}")
            print(f"内容边界: {info2['content_bbox']}")
            if not info2['needs_expansion']:
                print("✅ 所有内容现在都在页面内")
            else:
                print("⚠️  仍有内容超出，可能需要更大的margin")

        print("=" * 70)
