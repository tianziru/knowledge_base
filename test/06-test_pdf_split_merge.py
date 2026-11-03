"""纯函数单测：PDF 页窗拆分范围、图片引用改写、MD 合并顺序。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.import_process.utils.pdf_split import (  # noqa: E402
    compute_page_ranges,
    merge_part_markdowns,
    rewrite_image_refs,
    split_pdf_by_pages,
)


class TestComputePageRanges(unittest.TestCase):
    def test_no_split_when_within_limit(self):
        self.assertEqual(compute_page_ranges(180, 180), [(1, 180)])
        self.assertEqual(compute_page_ranges(1, 180), [(1, 1)])

    def test_split_boundaries(self):
        self.assertEqual(compute_page_ranges(181, 180), [(1, 180), (181, 181)])
        self.assertEqual(compute_page_ranges(360, 180), [(1, 180), (181, 360)])
        self.assertEqual(compute_page_ranges(361, 180), [(1, 180), (181, 360), (361, 361)])


class TestRewriteImageRefs(unittest.TestCase):
    def test_renames_markdown_image_links(self):
        md = "见图 ![a](images/0.jpg) 与 ![b](./images/1.png)"
        out = rewrite_image_refs(md, {"0.jpg": "p0_0.jpg", "1.png": "p0_1.png"})
        self.assertIn("images/p0_0.jpg", out)
        self.assertIn("images/p0_1.png", out)
        self.assertNotIn("images/0.jpg", out)


class TestMergePartMarkdowns(unittest.TestCase):
    def test_merge_order_and_image_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part0 = root / "part0"
            part1 = root / "part1"
            (part0 / "images").mkdir(parents=True)
            (part1 / "images").mkdir(parents=True)
            (part0 / "images" / "0.jpg").write_bytes(b"img0")
            (part1 / "images" / "0.jpg").write_bytes(b"img1")
            (part0 / "full.md").write_text("段0 ![x](images/0.jpg)\n", encoding="utf-8")
            (part1 / "full.md").write_text("段1 ![y](images/0.jpg)\n", encoding="utf-8")

            final_dir = root / "final"
            md_path = merge_part_markdowns(
                part_md_dirs=[part0, part1],
                final_dir=final_dir,
                stem="手册",
                part_labels=["p1-2", "p3-4"],
            )
            content = md_path.read_text(encoding="utf-8")
            self.assertTrue(md_path.name == "手册.md")
            self.assertLess(content.index("段0"), content.index("段1"))
            images = list((final_dir / "images").iterdir())
            self.assertEqual(len(images), 2)
            # 两段同名图必须都保留且 MD 中可引用
            self.assertEqual(content.count("](images/"), 2)
            for img in images:
                self.assertIn(img.name, content)


class TestSplitPdfByPages(unittest.TestCase):
    def test_split_creates_parts(self):
        import fitz

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "demo.pdf"
            doc = fitz.open()
            for _ in range(5):
                doc.new_page()
            doc.save(src)
            doc.close()

            parts = split_pdf_by_pages(src, root / "parts", max_pages=2)
            self.assertEqual(len(parts), 3)
            self.assertEqual([(s, e) for _, s, e in parts], [(1, 2), (3, 4), (5, 5)])
            for path, _, _ in parts:
                self.assertTrue(path.is_file())
                with fitz.open(path) as d:
                    self.assertGreaterEqual(d.page_count, 1)


if __name__ == "__main__":
    unittest.main()
