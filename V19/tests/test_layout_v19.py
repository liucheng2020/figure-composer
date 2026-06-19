"""V19 layout and settings tests."""
import os
import sys
import tempfile
import unittest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layout_engine import LayoutEngine
from pdf_utils import PDFInfo
from settings_manager import DEFAULT_SETTINGS, load_settings, save_settings
from gui_editor import FigureCombinerGUI, calculate_export_canvas
from provenance_utils import load_figure_provenance, build_composition_provenance


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

    def test_asymmetric_rows_fill_width_and_align_row_widths(self):
        engine = LayoutEngine(297, 210, margin_mm=5, spacing_mm=5)
        items = [
            FakeItem(40, 30, "A"),
            FakeItem(50, 40, "B"),
            FakeItem(80, 50, "C"),
        ]
        out = engine.asymmetric_rows(items, [2, 1], span_left=5, top_y=5)
        self.assertEqual([item.label for item in out], ["A", "B", "C"])

        top_row = out[:2]
        bottom_row = out[2:]
        top_left = min(item.x for item in top_row)
        top_right = max(item.x + item.width for item in top_row)
        bottom_left = min(item.x for item in bottom_row)
        bottom_right = max(item.x + item.width for item in bottom_row)
        self.assertAlmostEqual(top_left, 5.0, places=6)
        self.assertAlmostEqual(top_right, 292.0, places=6)
        self.assertAlmostEqual(bottom_left, 5.0, places=6)
        self.assertAlmostEqual(bottom_right, 292.0, places=6)
        self.assertGreater(bottom_row[0].y, top_row[0].y)


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


class CanvasSizeSyncTests(unittest.TestCase):
    def test_canvas_size_change_updates_current_canvas_dimensions(self):
        class FakeCanvas:
            canvas_width = 297
            canvas_height = 210

        class FakeWindow:
            current_canvas = FakeCanvas()
            show_ruler = False

            def get_canvas_width(self):
                return 210

            def get_canvas_height(self):
                return 297

            def update_canvas_rectangle(self):
                self.rectangle_updated = True

        fake = FakeWindow()
        FigureCombinerGUI.on_canvas_size_changed(fake)
        self.assertEqual(fake.current_canvas.canvas_width, 210)
        self.assertEqual(fake.current_canvas.canvas_height, 297)
        self.assertTrue(fake.rectangle_updated)


class ExportCanvasBoundsTests(unittest.TestCase):
    def test_export_canvas_crops_blank_a4_space_when_auto_crop_enabled(self):
        layouts = [
            FakeItem(40, 30, "A"),
            FakeItem(50, 20, "B"),
        ]
        layouts[0].x = 10
        layouts[0].y = 20
        layouts[1].x = 70
        layouts[1].y = 60
        shifted, width, height = calculate_export_canvas(
            layouts, 297, 210, padding=2, auto_crop=True)

        self.assertEqual(width, 114)
        self.assertEqual(height, 64)
        self.assertEqual(shifted[0].x, 2)
        self.assertEqual(shifted[0].y, 2)
        self.assertEqual(shifted[1].x, 62)
        self.assertEqual(shifted[1].y, 42)

    def test_export_canvas_expands_and_shifts_to_include_all_figures(self):
        layouts = [
            FakeItem(40, 30, "A"),
            FakeItem(50, 20, "B"),
        ]
        layouts[0].x = -10
        layouts[0].y = -5
        layouts[1].x = 280
        layouts[1].y = 190
        shifted, width, height = calculate_export_canvas(
            layouts, 297, 210, padding=2, auto_crop=False)

        self.assertEqual(width, 344)
        self.assertEqual(height, 219)
        self.assertEqual(shifted[0].x, 2)
        self.assertEqual(shifted[0].y, 2)
        self.assertEqual(shifted[1].x, 292)
        self.assertEqual(shifted[1].y, 197)
        self.assertEqual(layouts[0].x, -10)
        self.assertEqual(layouts[0].y, -5)


class ProvenanceUtilsTests(unittest.TestCase):
    def test_load_figure_provenance_finds_sidecar_next_to_figure(self):
        with tempfile.TemporaryDirectory() as tmp:
            figure_path = os.path.join(tmp, "01_umap.pdf")
            sidecar_path = os.path.join(tmp, "01_umap.provenance.json")
            open(figure_path, "wb").close()
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump({
                    "figure_file": "01_umap.pdf",
                    "best_match": {"code_file": "scripts/plot_umap.R"},
                    "confidence": "high",
                }, f)
            provenance = load_figure_provenance(figure_path)
        self.assertEqual(provenance["best_match"]["code_file"], "scripts/plot_umap.R")
        self.assertEqual(provenance["_provenance_path"], sidecar_path)

    def test_build_composition_provenance_links_panels_to_sidecars(self):
        layout = FakeItem(40, 30, "A")
        layout.x = 5
        layout.y = 6
        layout.pdf_info.provenance = {
            "figure_file": "A.pdf",
            "figure_path_rel": "figures/A.pdf",
            "best_match": {
                "code_file": "scripts/a.R",
                "code_lines": [10, 20],
            },
            "confidence": "high",
            "_provenance_path": "D:/project/A.provenance.json",
        }
        manifest = build_composition_provenance(
            base_path="D:/export/Figure1",
            canvas_name="Figure1",
            layouts=[layout],
            project_root="D:/project",
        )
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["composition"]["base_path"], "D:/export/Figure1")
        self.assertEqual(manifest["panels"][0]["panel_label"], "A")
        self.assertEqual(manifest["panels"][0]["code_file"], "scripts/a.R")
        self.assertEqual(manifest["panels"][0]["code_lines"], [10, 20])
        self.assertEqual(manifest["panels"][0]["provenance_path_rel"], "A.provenance.json")
        self.assertNotIn("provenance", manifest["panels"][0])


class StartupBehaviorTests(unittest.TestCase):
    def test_startup_does_not_prompt_to_recover_autosaves(self):
        run_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run_v19.py")
        with open(run_script, "r", encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("offer_recovery_if_any", source)


if __name__ == "__main__":
    unittest.main()
