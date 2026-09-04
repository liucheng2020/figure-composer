"""V20 Agent CLI 测试。"""

import argparse
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import fitz


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_cli import apply_order, compose, parse_layout_spec
from pdf_utils import PDFInfo


def create_pdf(path, pages, width=400, height=300):
    """生成小型矢量 PDF 测试输入。"""
    document = fitz.open()
    for page_index in range(pages):
        page = document.new_page(width=width, height=height)
        page.insert_text((40, 60), f"Page {page_index + 1}", fontsize=24)
        page.draw_rect(fitz.Rect(30, 30, width - 30, height - 30), color=(0, 0, 0))
    document.save(str(path))
    document.close()


class LayoutSpecTests(unittest.TestCase):
    def test_grid_and_auto_layouts(self):
        grid = parse_layout_spec("4x4", 16)
        self.assertEqual(grid.kind, "grid")
        self.assertEqual(grid.counts, (4, 4, 4, 4))

        auto = parse_layout_spec("auto", 5)
        self.assertEqual(auto.kind, "grid")
        self.assertEqual(auto.counts, (3, 2))

    def test_asymmetric_and_chinese_layouts(self):
        columns = parse_layout_spec("columns:2+1", 3)
        self.assertEqual(columns.kind, "columns")
        self.assertEqual(columns.counts, (2, 1))

        chinese = parse_layout_spec("上二下一", 3)
        self.assertEqual(chinese.kind, "rows")
        self.assertEqual(chinese.counts, (2, 1))

    def test_layout_count_must_match(self):
        with self.assertRaises(ValueError):
            parse_layout_spec("columns:2+1", 4)


class InputOrderTests(unittest.TestCase):
    def test_explicit_order_is_exact(self):
        first = PDFInfo("a.pdf", "a.pdf", 10, 10, 1, (1, "a"))
        second = PDFInfo("b.pdf", "b.pdf", 10, 10, 1, (1, "b"))
        ordered = apply_order([first, second], ["b.pdf", "a.pdf"])
        self.assertEqual([item.filename for item in ordered], ["b.pdf", "a.pdf"])

        with self.assertRaises(ValueError):
            apply_order([first, second], ["a.pdf"])


class AgentCliEndToEndTests(unittest.TestCase):
    def test_compose_split_multipage_and_validate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "input"
            output_dir = root / "output"
            source_dir.mkdir()
            create_pdf(source_dir / "01_multi.pdf", pages=2, width=300, height=500)
            create_pdf(source_dir / "02_single.pdf", pages=1, width=500, height=300)

            args = argparse.Namespace(
                input=str(source_dir),
                output=str(output_dir),
                name="V20_test",
                layout="columns:2+1",
                fill_mode="equal-height",
                span_left=None,
                span_width=None,
                top=None,
                order=None,
                multipage="split",
                format="pdf",
                canvas_width=297.0,
                canvas_height=210.0,
                margin=5.0,
                spacing=5.0,
                padding=2.0,
                dpi=72,
                preview_dpi=36,
                label_fontsize=12,
                label_color="black",
                label_offset=0.25,
                label_bold=True,
                label_visible=True,
                preserve_canvas=False,
                overwrite=False,
            )
            paths = compose(args)

            with fitz.open(paths["pdf"]) as document:
                self.assertEqual(len(document), 1)

            with paths["validation"].open("r", encoding="utf-8") as file:
                validation = json.load(file)
            self.assertEqual(validation["status"], "PASS")
            self.assertEqual(validation["panel_count"], 3)
            self.assertEqual(validation["labels"], ["A", "B", "C"])

            with paths["layout"].open("r", encoding="utf-8") as file:
                manifest = json.load(file)
            self.assertEqual([panel["source_page"] for panel in manifest["panels"]], [1, 2, 1])

            with zipfile.ZipFile(paths["figbox"]) as archive:
                project = json.loads(archive.read("project.json").decode("utf-8"))
                assets = [
                    name for name in archive.namelist()
                    if name.startswith("assets/") and not name.endswith("/")
                ]
            self.assertEqual(project["version"], "20.0")
            self.assertEqual(len(project["layouts"]), 3)
            self.assertEqual(len(assets), 3)


if __name__ == "__main__":
    unittest.main()
