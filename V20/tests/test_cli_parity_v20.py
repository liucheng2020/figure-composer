"""V20 CLI 与 GUI 结果型功能对齐测试。"""

import argparse
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz
from PIL import Image


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_cli import CHINESE_LAYOUTS, compose, handle_export, parse_layout_spec
from layout_engine import LayoutItem
from pdf_utils import PDFInfo
from project_ops import (
    LoadedProject,
    apply_boundary,
    apply_transform,
    parse_selector,
    save_project,
    smart_relayout,
)
import project_io


def fake_layout(label, x, y, width, height):
    info = PDFInfo(
        filepath=f"{label}.pdf",
        filename=f"{label}.pdf",
        width=width,
        height=height,
        aspect_ratio=width / height,
        sort_key=(0, ord(label) - 65),
        original_path=f"D:/source/{label}.pdf",
    )
    return LayoutItem(info, x, y, width, height, 0, label)


def create_pdf(path, width=400, height=300, pages=1):
    document = fitz.open()
    for index in range(pages):
        page = document.new_page(width=width, height=height)
        page.insert_text((30, 50), f"Panel {index + 1}", fontsize=20)
        page.draw_rect(fitz.Rect(20, 20, width - 20, height - 20), color=(0, 0, 0))
    document.save(str(path))
    document.close()


def compose_args(source_dir, output_dir, name="Figure"):
    return argparse.Namespace(
        input=str(source_dir), output=str(output_dir), name=name,
        layout="auto", fill_mode="equal-height", span_left=None,
        span_width=None, top=None, order=None, multipage="first", format="pdf",
        canvas_width=297.0, canvas_height=210.0, margin=5.0, spacing=5.0,
        padding=2.0, dpi=72, preview_dpi=36,
        label_fontsize=12, label_color="black", label_offset=0.25,
        label_bold=True, label_visible=True,
        preserve_canvas=False, overwrite=False,
    )


class SmartGridParityTests(unittest.TestCase):
    def test_all_gui_chinese_presets_parse(self):
        self.assertEqual(len(CHINESE_LAYOUTS), 18)
        for name, (kind, counts) in CHINESE_LAYOUTS.items():
            spec = parse_layout_spec(name, sum(counts))
            self.assertEqual(spec.kind, kind, name)
            self.assertEqual(spec.counts, counts, name)

    def test_equal_height_uniform_and_no_scale(self):
        base = [
            fake_layout("A", 0, 0, 40, 20),
            fake_layout("B", 0, 0, 30, 30),
            fake_layout("C", 0, 0, 50, 25),
            fake_layout("D", 0, 0, 20, 40),
        ]
        spec = parse_layout_spec("2x2", 4)

        equal_height = [fake_layout(item.label, 0, 0, item.width, item.height) for item in base]
        smart_relayout(equal_height, [0, 1, 2, 3], spec, "equal-height", 297, 210, 5, 5)
        self.assertAlmostEqual(equal_height[0].height, equal_height[1].height)
        self.assertAlmostEqual(equal_height[2].height, equal_height[3].height)

        uniform = [fake_layout(item.label, 0, 0, item.width, item.height) for item in base]
        first_ratio = uniform[0].width / uniform[1].width
        smart_relayout(uniform, [0, 1, 2, 3], spec, "uniform-scale", 297, 210, 5, 5)
        self.assertAlmostEqual(uniform[0].width / uniform[1].width, first_ratio)

        no_scale = [fake_layout(item.label, 0, 0, item.width, item.height) for item in base]
        original_sizes = [(item.width, item.height) for item in no_scale]
        smart_relayout(no_scale, [0, 1, 2, 3], spec, "no-scale", 297, 210, 5, 5)
        self.assertEqual([(item.width, item.height) for item in no_scale], original_sizes)


class EditParityTests(unittest.TestCase):
    def make_layouts(self):
        return [
            fake_layout("A", 5, 5, 40, 20),
            fake_layout("B", 60, 20, 30, 30),
            fake_layout("C", 110, 40, 50, 25),
        ]

    def test_size_alignment_distribution_spacing_and_rotation(self):
        layouts = self.make_layouts()
        apply_transform(layouts, [0, 1, 2], "same-width")
        self.assertEqual(len({round(item.width, 6) for item in layouts}), 1)

        apply_transform(layouts, [0, 1, 2], "align-top")
        self.assertEqual(len({round(item.y, 6) for item in layouts}), 1)

        layouts[0].x, layouts[1].x, layouts[2].x = 0, 20, 100
        apply_transform(layouts, [0, 1, 2], "distribute-horizontal")
        self.assertAlmostEqual(layouts[1].x, 50)

        apply_transform(layouts, [0, 1, 2], "spacing-horizontal", value=5)
        self.assertAlmostEqual(layouts[1].x, layouts[0].x + layouts[0].width + 5)

        apply_transform(layouts, [0, 1], "rotate", angle=90, absolute=False)
        self.assertEqual(layouts[0].rotation, 90)
        old_x, old_y = layouts[0].x, layouts[0].y
        apply_transform(layouts, [0], "move", x=None, y=None, dx=3, dy=4)
        self.assertEqual((layouts[0].x, layouts[0].y), (old_x + 3, old_y + 4))

    def test_relabel_delete_and_selector_range(self):
        layouts = self.make_layouts()
        self.assertEqual(parse_selector(layouts, "A-C"), [0, 1, 2])
        apply_transform(layouts, [2], "relabel", new_label="A")
        self.assertEqual([item.pdf_info.filename for item in layouts], ["C.pdf", "A.pdf", "B.pdf"])
        apply_transform(layouts, [1], "delete")
        self.assertEqual([item.label for item in layouts], ["A", "B"])

    def test_every_geometry_operation_is_callable(self):
        operations = [
            ("scale", {"factor": 0.95}),
            ("same-width", {}),
            ("same-height", {}),
            ("align-left", {}),
            ("align-right", {}),
            ("align-top", {}),
            ("align-bottom", {}),
            ("align-h-center", {}),
            ("align-v-center", {}),
            ("distribute-horizontal", {}),
            ("distribute-vertical", {}),
            ("spacing-horizontal", {"value": 3}),
            ("spacing-vertical", {"value": 3}),
            ("rotate", {"angle": 270, "absolute": True}),
            ("move", {"x": None, "y": None, "dx": 2, "dy": 4}),
            ("resize", {"width": 55, "height": None}),
        ]
        for operation, values in operations:
            with self.subTest(operation=operation):
                layouts = self.make_layouts()
                apply_transform(layouts, [0, 1, 2], operation, **values)
                self.assertEqual(len(layouts), 3)


class ProjectAndExportParityTests(unittest.TestCase):
    def test_images_compose_and_existing_project_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "input"
            compose_dir = root / "compose"
            export_dir = root / "export"
            source_dir.mkdir()
            create_pdf(source_dir / "01_pdf.pdf")
            Image.new("RGB", (200, 120), "white").save(source_dir / "02_image.png")

            paths = compose(compose_args(source_dir, compose_dir))
            with paths["validation"].open("r", encoding="utf-8") as file:
                self.assertEqual(json.load(file)["panel_count"], 2)

            export_args = argparse.Namespace(
                project=str(paths["figbox"]), output=str(export_dir), name="Exported",
                format="pdf", dpi=72, preview_dpi=36, padding=2.0,
                crop="project", overwrite=False,
            )
            export_paths = handle_export(export_args)
            with export_paths["validation"].open("r", encoding="utf-8") as file:
                self.assertEqual(json.load(file)["status"], "PASS")

    def test_boundary_derivative_is_embedded_in_figbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_pdf = root / "source.pdf"
            source_project = root / "source.figbox"
            output_project = root / "expanded.figbox"
            create_pdf(source_pdf)
            data = {
                "version": "20.0", "canvas_name": "Boundary", "canvas_width": 297,
                "canvas_height": 210, "settings": {},
                "layouts": [{
                    "pdf_path": str(source_pdf), "original_path": str(source_pdf),
                    "x": 5, "y": 5, "width": 100, "height": 75,
                    "rotation": 0, "label": "A", "expand_boundary": False,
                    "expanded_filepath": None, "cumulative_margin": 0,
                    "provenance": None,
                }],
            }
            project_io.pack_figbox(source_project, data)

            with LoadedProject.open(source_project) as session:
                apply_boundary(
                    session.layouts, [0], "expand", 10,
                    "left,right,top,bottom", session.temp_dir)
                save_project(session, output_project)

            with zipfile.ZipFile(output_project) as archive:
                project = json.loads(archive.read("project.json").decode("utf-8"))
                assets = [name for name in archive.namelist() if name.startswith("assets/")]
            self.assertEqual(len(assets), 2)
            self.assertTrue(project["layouts"][0]["expanded_filepath"].startswith("assets/"))


if __name__ == "__main__":
    unittest.main()
