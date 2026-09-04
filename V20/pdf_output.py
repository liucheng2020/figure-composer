"""PDF output module for exporting combined figures."""

import fitz  # PyMuPDF
from typing import List
from layout_engine import LayoutItem
from pdf_utils import mm_to_points
from PIL import Image, ImageDraw, ImageFont
import io


def export_combined_pdf(layouts: List[LayoutItem],
                        canvas_width_mm: float,
                        canvas_height_mm: float,
                        output_path: str,
                        dpi: int = 300,
                        label_bold: bool = True,
                        label_offset: float = 0.25,
                        label_fontsize: int = 12,
                        label_color=(0, 0, 0),
                        label_visible: bool = True):
    """
    Export combined PDF with all figures arranged according to layouts.

    Args:
        layouts: List of layout items with position and size information
        canvas_width_mm: Canvas width in millimeters
        canvas_height_mm: Canvas height in millimeters
        output_path: Output PDF file path
        dpi: Output resolution (affects label rendering quality)
    """
    # Convert mm to points
    canvas_width_pt = mm_to_points(canvas_width_mm)
    canvas_height_pt = mm_to_points(canvas_height_mm)

    # Create new PDF document
    output_doc = fitz.open()
    output_page = output_doc.new_page(width=canvas_width_pt, height=canvas_height_pt)

    # Process each figure
    for layout in layouts:
        # V6: Use effective PDF path (expanded boundary if enabled)
        from pdf_utils import get_effective_pdf_path
        pdf_path = get_effective_pdf_path(layout.pdf_info)

        # Open source PDF
        src_doc = fitz.open(pdf_path)
        src_page = src_doc[0]

        # Calculate position and size in points
        x_pt = mm_to_points(layout.x)
        y_pt = mm_to_points(layout.y)
        width_pt = mm_to_points(layout.width)
        height_pt = mm_to_points(layout.height)

        # V15 FIX: Normalize rotation to 0, 90, 180, 270
        rotation = int(layout.rotation) % 360
        
        # V15 FIX: For 90 or 270 degree rotation, the target rect needs adjustment
        # because the rotated content will have swapped width/height
        if rotation in (90, 270):
            # For 90/270 rotation, we need to adjust the target rectangle
            # The content will be rotated, so we use the original rect
            # but PyMuPDF handles this internally with keep_proportion
            target_rect = fitz.Rect(x_pt, y_pt, x_pt + width_pt, y_pt + height_pt)
        else:
            target_rect = fitz.Rect(x_pt, y_pt, x_pt + width_pt, y_pt + height_pt)

        # Insert the page with transformation
        # V15 FIX: Use clip=src_page.rect to ensure entire source page is used
        output_page.show_pdf_page(
            target_rect,
            src_doc,
            0,
            clip=src_page.rect,  # V15: Use full source page
            rotate=rotation,
            keep_proportion=True
        )

        src_doc.close()

        # Add label (A, B, C, etc.)
        if label_visible:
            add_label(
                output_page, layout, x_pt, y_pt, dpi, label_bold,
                label_offset, label_fontsize, label_color)

    # Save output PDF
    output_doc.save(output_path, garbage=4, deflate=True)
    output_doc.close()


def add_label(page, layout: LayoutItem, x_pt: float, y_pt: float, dpi: int,
              bold: bool = True, label_offset: float = 0.25,
              font_size: int = 12, color=(0, 0, 0)):
    """
    Add label text to the figure.
    Label is placed outside the figure at top-left with no background.

    Args:
        page: PDF page object
        layout: Layout item with label information
        x_pt: X position in points
        y_pt: Y position in points
        dpi: DPI for text rendering quality
        bold: Whether to use bold font
        label_offset: Label offset distance in mm (default 0.25mm)
    """
    # Label configuration
    label_text = layout.label
    # Use bold font if requested
    font_name = "hebo" if bold else "helv"  # Helvetica-Bold or Helvetica

    # Calculate label position (outside, top-left)
    # Use label_offset from GUI settings
    # 1mm ≈ 2.834645669 points
    label_x = x_pt - label_offset * 2.834645669
    label_y = y_pt - label_offset * 2.834645669

    # Insert text (no background, no border)
    text_point = fitz.Point(label_x, label_y)

    # Use insert_text for better quality
    page.insert_text(
        text_point,
        label_text,
        fontsize=font_size,
        fontname=font_name,
        color=color,
        render_mode=0  # Fill text
    )


def create_preview_pdf(layouts: List[LayoutItem],
                       canvas_width_mm: float,
                       canvas_height_mm: float,
                       output_path: str):
    """
    Create a low-resolution preview PDF (faster, for checking layout).

    Args:
        layouts: List of layout items
        canvas_width_mm: Canvas width in millimeters
        canvas_height_mm: Canvas height in millimeters
        output_path: Output PDF file path
    """
    # Use lower DPI for preview
    export_combined_pdf(layouts, canvas_width_mm, canvas_height_mm, output_path, dpi=72)


def export_combined_image(layouts: List[LayoutItem],
                          canvas_width_mm: float,
                          canvas_height_mm: float,
                          output_path: str,
                          image_format: str = 'png',
                          dpi: int = 300,
                          label_bold: bool = True,
                          label_offset: float = 0.25,
                          label_fontsize: int = 12,
                          label_color=(0, 0, 0),
                          label_visible: bool = True):
    """
    Export combined figure as PNG or TIF image.

    Args:
        layouts: List of layout items with position and size information
        canvas_width_mm: Canvas width in millimeters
        canvas_height_mm: Canvas height in millimeters
        output_path: Output image file path
        image_format: 'png' or 'tif'
        dpi: Output resolution
    """
    # Convert mm to pixels
    mm_to_px = dpi / 25.4  # 1 inch = 25.4 mm
    canvas_width_px = int(canvas_width_mm * mm_to_px)
    canvas_height_px = int(canvas_height_mm * mm_to_px)

    # Create blank canvas - V8修复：统一使用RGBA支持透明度
    if image_format == 'tif':
        canvas = Image.new('RGBA', (canvas_width_px, canvas_height_px), (255, 255, 255, 255))
    else:  # png (default)
        canvas = Image.new('RGBA', (canvas_width_px, canvas_height_px), (255, 255, 255, 255))

    draw = ImageDraw.Draw(canvas)

    # Process each figure
    for idx, layout in enumerate(layouts):
        try:
            # V6: Use effective PDF path (expanded boundary if enabled)
            from pdf_utils import get_effective_pdf_path
            pdf_path = get_effective_pdf_path(layout.pdf_info)

            # Open and render PDF page to image
            src_doc = fitz.open(pdf_path)
            src_page = src_doc[0]

            # Calculate position and size in pixels
            x_px = int(layout.x * mm_to_px)
            y_px = int(layout.y * mm_to_px)
            width_px = int(layout.width * mm_to_px)
            height_px = int(layout.height * mm_to_px)

            # V15 FIX: Ensure valid dimensions (minimum 1 pixel)
            width_px = max(1, width_px)
            height_px = max(1, height_px)

            # V15 FIX: Calculate zoom based on target size to avoid scaling issues
            # Get source page dimensions
            src_width = src_page.rect.width
            src_height = src_page.rect.height
            
            # V15 FIX: Avoid division by zero
            if src_width <= 0 or src_height <= 0:
                print(f"警告: 图片 {idx} 源尺寸无效 ({src_width}x{src_height})")
                continue
            
            # V19 性能优化：直接按"目标像素尺寸"渲染，而不是先按 max(dpi/72,…) 过度渲染
            # 再缩小。最终图里该面板就只有 width_px×height_px 个像素，所以按目标尺寸
            # 渲染即可获得全部清晰度，却避免了对点很多的矢量图（如单细胞 UMAP）做几倍
            # 于实际所需的光栅化，导出可大幅提速且不损失清晰度。
            zoom_x = width_px / src_width
            zoom_y = height_px / src_height
            mat = fitz.Matrix(zoom_x, zoom_y)
            pix = src_page.get_pixmap(matrix=mat, alpha=True)

            # Convert pixmap to PIL Image - V8修复：统一使用RGBA
            img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)

            try:
                resample_filter = Image.Resampling.LANCZOS  # Pillow >= 9.1.0
            except AttributeError:
                resample_filter = Image.LANCZOS  # Pillow < 9.1.0

            # 渲染像素数因取整可能与目标差 1px，必要时再轻量校正到精确目标尺寸
            if (pix.width, pix.height) != (width_px, height_px):
                img = img.resize((width_px, height_px), resample_filter)

            # V15 FIX: Calculate paste position, adjusting for rotation
            paste_x = x_px
            paste_y = y_px

            # Apply rotation if needed
            if layout.rotation != 0:
                # V15 FIX: Normalize rotation angle
                rotation_angle = layout.rotation % 360
                
                # V15 FIX: When using expand=True, the image size changes after rotation
                # We need to adjust the paste position to keep the center aligned
                old_width, old_height = img.size
                old_center_x = old_width / 2
                old_center_y = old_height / 2
                
                # V8修复：RGBA图像使用正确的fillcolor格式
                img = img.rotate(-rotation_angle, expand=True, fillcolor=(255, 255, 255, 255))
                
                # V15 FIX: Calculate new paste position to center the rotated image
                new_width, new_height = img.size
                new_center_x = new_width / 2
                new_center_y = new_height / 2
                
                # The center of the original image should stay at the same position
                # Original center position: (x_px + old_width/2, y_px + old_height/2)
                # New paste position should be such that new center aligns with original center
                paste_x = int(x_px + old_center_x - new_center_x)
                paste_y = int(y_px + old_center_y - new_center_y)

            # V15 FIX: Ensure paste coordinates and image fit within canvas
            # PIL's paste can handle negative coordinates and overflow gracefully
            # by only pasting the visible portion, but we need to ensure consistency
            
            # Paste onto canvas
            # V8修复：对于RGBA图像使用自身作为mask以保持透明度
            # V15 FIX: Use adjusted paste position
            if img.mode == 'RGBA':
                canvas.paste(img, (paste_x, paste_y), img)
            else:
                canvas.paste(img, (paste_x, paste_y))

            src_doc.close()

            # Add label
            if label_visible:
                add_label_to_image(
                    draw, layout, x_px, y_px, mm_to_px, label_bold,
                    label_offset, label_fontsize, label_color)

        except Exception as e:
            # V8修复：处理单个图片失败时继续处理其他图片
            print(f"处理图片 {idx} ({layout.label}) 时出错: {e}")
            import traceback
            traceback.print_exc()
            # 继续处理下一个图片
            continue

    # Save image - V8修复：只支持PNG和TIF格式
    if image_format == 'tif':
        # V8修复：TIF格式转换为RGB（TIF不常用透明通道）
        if canvas.mode == 'RGBA':
            # 创建白色背景
            rgb_canvas = Image.new('RGB', canvas.size, (255, 255, 255))
            rgb_canvas.paste(canvas, (0, 0), canvas)
            rgb_canvas.save(output_path, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
        else:
            canvas.save(output_path, 'TIFF', compression='tiff_lzw', dpi=(dpi, dpi))
    else:  # png (default)
        canvas.save(output_path, 'PNG', dpi=(dpi, dpi))


def add_label_to_image(draw, layout: LayoutItem, x_px: int, y_px: int,
                       mm_to_px: float, bold: bool = True,
                       label_offset: float = 0.25, font_size_pt: int = 12,
                       color=(0, 0, 0)):
    """
    Add label text to image.
    Label is placed outside the figure at top-left with no background.

    Args:
        draw: ImageDraw object
        layout: Layout item with label information
        x_px: X position in pixels
        y_px: Y position in pixels
        mm_to_px: Conversion factor from mm to pixels
        bold: Whether to use bold font
        label_offset: Label offset distance in mm (default 0.25mm)
    """
    label_text = layout.label
    dpi = mm_to_px * 25.4
    font_size = max(1, int(round(font_size_pt * dpi / 72)))

    # Try to use Arial font (bold or regular), fallback to default
    try:
        if bold:
            font = ImageFont.truetype("arialbd.ttf", font_size)  # Arial Bold
        else:
            font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            if bold:
                font = ImageFont.truetype("Arial Bold.ttf", font_size)
            else:
                font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            try:
                # Try system fonts on different platforms
                import platform
                if platform.system() == 'Windows':
                    if bold:
                        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
                    else:
                        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                elif platform.system() == 'Darwin':  # macOS
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                else:  # Linux
                    if bold:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
                    else:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size)
            except:
                font = ImageFont.load_default()

    # V14 FIX: Calculate text height to avoid overlapping the figure
    # PIL's draw.text positions at top-left corner, unlike PDF which uses baseline
    # We need to offset upward by the text height
    try:
        # Get text bounding box to calculate height
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_height = bbox[3] - bbox[1]  # bottom - top
    except:
        # If textbbox not available (older Pillow), use estimated height
        text_height = int(font_size * 1.2)  # Estimated line height

    # Calculate label position (outside, top-left)
    # Use label_offset from GUI settings
    label_x = x_px - int(label_offset * mm_to_px)
    label_y = y_px - int(label_offset * mm_to_px) - text_height  # V14: Subtract text height

    # Draw text (no background)
    if isinstance(color, tuple) and color and max(color) <= 1:
        color = tuple(int(round(channel * 255)) for channel in color)
    draw.text((label_x, label_y), label_text, fill=color, font=font)
