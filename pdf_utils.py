"""PDF processing utilities for reading and analyzing PDF files."""

import fitz  # PyMuPDF
import re
import os
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class PDFInfo:
    """Information about a PDF file."""
    filepath: str
    filename: str
    width: float  # in points
    height: float  # in points
    aspect_ratio: float
    sort_key: Tuple  # for sorting
    expand_boundary: bool = False  # V6: 是否扩展PDF边界以显示被裁剪的内容
    expanded_filepath: str = None  # V6: 扩展边界后的临时文件路径
    cumulative_margin: int = 0  # V6: 累积的扩展边距（用于基于原始PDF多次扩展）

    @property
    def is_tall(self) -> bool:
        """Check if image is taller than wide."""
        return self.aspect_ratio < 0.67

    @property
    def is_wide(self) -> bool:
        """Check if image is wider than tall."""
        return self.aspect_ratio > 1.5

    @property
    def is_square(self) -> bool:
        """Check if image is approximately square."""
        return 0.67 <= self.aspect_ratio <= 1.5


def parse_filename(filename: str) -> Tuple:
    """
    Parse filename to extract sorting key.
    Supports ALL PDF filenames including: 1.pdf, 2.pdf, FDPS_drug_effects_combined.pdf

    V7: Enhanced to handle ANY filename format
    Returns tuple for natural sorting with priority system.
    """
    # Remove extension
    name = os.path.splitext(filename)[0]

    # Extract all numbers
    numbers = re.findall(r'\d+', name)

    # V7 FIX: Use priority system to ensure all keys are comparable
    if numbers:
        # Files with numbers get priority 0 (sort first)
        # Convert numbers to integers for natural sorting
        sort_key = [0] + [int(num) for num in numbers]
        return tuple(sort_key)
    else:
        # Files without numbers get priority 1 (sort after numbered files)
        # Sort alphabetically by full filename (case-insensitive)
        return (1, name.lower())


def scan_pdf_folder(folder_path: str) -> List[PDFInfo]:
    """
    Scan folder for ALL PDF files and extract their information.

    V7: Enhanced to handle ANY PDF filename format

    Args:
        folder_path: Path to folder containing PDF files

    Returns:
        List of PDFInfo objects sorted by filename
    """
    pdf_files = []

    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith('.pdf'):
            continue

        filepath = os.path.join(folder_path, filename)

        try:
            # Open PDF and get first page dimensions
            doc = fitz.open(filepath)
            if len(doc) == 0:
                print(f"Warning: {filename} has no pages, skipping")
                doc.close()
                continue

            page = doc[0]

            # Get page dimensions
            rect = page.rect
            width = rect.width
            height = rect.height
            aspect_ratio = width / height if height > 0 else 1.0

            # Check if PDF is vector-based
            is_vector = check_if_vector(page)
            if not is_vector:
                print(f"Info: {filename} may contain rasterized content")

            # V7: Parse filename to get sort key
            sort_key = parse_filename(filename)

            pdf_info = PDFInfo(
                filepath=filepath,
                filename=filename,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                sort_key=sort_key
            )

            pdf_files.append(pdf_info)
            print(f"✓ Loaded: {filename} (sort_key: {sort_key})")
            doc.close()

        except Exception as e:
            print(f"✗ Error reading {filename}: {e}")
            print(f"  Please check if the file is a valid PDF")
            continue

    # Sort by filename (natural sorting)
    pdf_files.sort(key=lambda x: x.sort_key)

    print(f"\n✓ Total loaded: {len(pdf_files)} PDF files")
    return pdf_files


def check_if_vector(page) -> bool:
    """
    Check if a PDF page contains vector graphics.
    Returns True if page has paths/vector content.
    """
    # Get page drawings (vector paths)
    drawings = page.get_drawings()

    # Get images on page
    images = page.get_images()

    # If has drawings and few/no images, likely vector
    return len(drawings) > 0 or len(images) == 0


def get_pdf_page_as_pixmap(filepath: str, dpi: int = 72) -> fitz.Pixmap:
    """
    Render PDF page as pixmap for preview.

    Args:
        filepath: Path to PDF file
        dpi: Resolution for rendering (72 for screen, 300 for print)

    Returns:
        Pixmap object
    """
    doc = fitz.open(filepath)
    page = doc[0]

    # Calculate zoom factor
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    return pix


def points_to_mm(points: float) -> float:
    """Convert points to millimeters."""
    return points * 0.352778


def mm_to_points(mm: float) -> float:
    """Convert millimeters to points."""
    return mm / 0.352778


def get_effective_pdf_path(pdf_info):
    """
    获取PDF的有效路径（如果启用了边界扩展，返回扩展后的路径）

    Args:
        pdf_info: PDFInfo对象

    Returns:
        str: PDF文件路径
    """
    if pdf_info.expand_boundary and pdf_info.expanded_filepath:
        return pdf_info.expanded_filepath
    return pdf_info.filepath


# Common canvas presets
CANVAS_PRESETS = {
    'A4横版': (297, 210),  # mm
    'A4竖版': (210, 297),
    '1366x768': (1366 * 0.264583, 768 * 0.264583),  # pixels to mm
    '1920x1080': (1920 * 0.264583, 1080 * 0.264583),
    '自定义': None
}
