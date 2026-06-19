"""V19 layout and settings tests."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layout_engine import LayoutEngine
from pdf_utils import PDFInfo
from settings_manager import DEFAULT_SETTINGS, load_settings, save_settings


class FakeItem:
    """Small stand-in for GUI selected items."""

    def __init__(self, width, height, label):
        self.width = width
        self.height = height
        self.label = label
        self.rotation = 0.0
        self.pdf_info = PDFInfo(
            filepath=f"{label}.pdf",
            filename=f"{label}.pdf",
            width=width,
            height=height,
            aspect_ratio=width / height,
            sort_key=(0, ord(label) - 65),
            original_path=f"D:/source/{label}.pdf",
        )


class LayoutEngineV19Tests(unittest.TestCase):
    def test_default_margin_is_5mm(self):
        engine = LayoutEngine(297, 210)
        self.assertEqual(engine.margin, 5.0)
        self.assertEqual(engine.available_width, 287.0)

    def test_parse_column_pattern(self):
        self.assertEqual(LayoutEngine.parse_column_pattern("2+1", 3), [2, 1])
        self.assertEqual(LayoutEngine.parse_column_pattern(" 1 + 2 ", 3), [1, 2])
        with self.assertRaises(ValueError):
            LayoutEngine.parse_column_pattern("2+2", 3)

    def test_asymmetric_columns_fill_width_and_align_total_height(self):
        engine = LayoutEngine(297, 210, margin_mm=5, spacing_mm=5)
        items = [
            FakeItem(40, 30, "A"),
            FakeItem(50, 40, "B"),
            FakeItem(80, 50, "C"),
        ]
        out = engine.asymmetric_columns(items, [2, 1], span_left=5, top_y=5)
        self.assertEqual([item.label for item in out], ["A", "B", "C"])

        left = min(item.x for item in out)
        right = max(item.x + item.width for item in out)
        self.assertAlmostEqual(left, 5.0, places=6)
        self.assertAlmostEqual(right, 292.0, places=6)

        left_col = out[:2]
        right_col = out[2:]
        left_height = sum(item.height for item in left_col) + engine.spacing
        right_height = sum(item.height for item in right_col)
        self.assertAlmostEqual(left_height, right_height, places=6)

        for src, placed in zip(items, out):
            self.assertAlmostEqual(
                placed.width / placed.height,
                src.width / src.height,
                places=6,
            )


class SettingsManagerV19Tests(unittest.TestCase):
    def test_default_settings_include_v19_defaults(self):
        settings = load_settings(path=None)
        self.assertEqual(settings["margin"], 5)
        self.assertEqual(settings["dpi"], 1000)
        self.assertTrue(settings["autosave_enabled"])

    def test_save_and_load_settings_merges_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings_v19.json")
            save_settings({"margin": 8, "theme": "dark"}, path=path)
            loaded = load_settings(path=path)
        self.assertEqual(loaded["margin"], 8)
        self.assertEqual(loaded["theme"], "dark")
        self.assertEqual(loaded["dpi"], DEFAULT_SETTINGS["dpi"])


class PDFInfoV19Tests(unittest.TestCase):
    def test_pdf_info_keeps_original_source_path(self):
        info = PDFInfo(
            filepath="D:/temp/converted.pdf",
            filename="source.png",
            width=100,
            height=50,
            aspect_ratio=2.0,
            sort_key=(1, "source"),
            original_path="D:/raw/source.png",
        )
        self.assertEqual(info.original_path, "D:/raw/source.png")


if __name__ == "__main__":
    unittest.main()
