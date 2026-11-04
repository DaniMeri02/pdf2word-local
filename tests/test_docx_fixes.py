"""Regression tests for python/pdf2word/docx_fixes.py (DOCX portability fixes).

Run: spike/.venv/bin/python -m unittest discover -s tests -p "test_*.py"

Origin: a user's diagnostic report (Word 2016 + ilovepdf PDF) showed tables with
equal grid columns instead of the real widths, "exact" row heights that cut text,
and a logo/address header built from multi-column sections with a "nextColumn"
break, which a phone viewer rendered on two pages.
"""

import io
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lxml import etree  # noqa: E402

from pdf2word import convert_unfixed  # noqa: E402
from pdf2word.docx_fixes import fix_docx  # noqa: E402
from test_charts import word_style_table_pdf  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def raw_pdf2docx(pdf: bytes) -> bytes:
    """The app's pipeline (chart pre-processing + pdf2docx) without the DOCX fixes."""
    return convert_unfixed(pdf)


def document(docx: bytes):
    return etree.fromstring(zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml"))


def texts(root) -> list[str]:
    return [t.text for t in root.iter(f"{{{W}}}t") if t.text]


def fixtures() -> dict[str, bytes]:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([sys.executable, str(ROOT / "spike" / "make_test_pdfs.py"), str(tmp)], check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "spike" / "replica_report_1.py"), str(tmp / "replica_report_1.pdf")],
                   check=True, capture_output=True)
    pdfs = {p.name: p.read_bytes() for p in sorted(tmp.glob("*.pdf")) if not p.name.startswith("protected")}
    pdfs["word_style_tables.pdf"] = word_style_table_pdf()
    return pdfs


class DocxFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import logging

        logging.getLogger().setLevel(logging.WARNING)
        cls.cases = {}
        for name, pdf in fixtures().items():
            raw = raw_pdf2docx(pdf)
            cls.cases[name] = (raw, fix_docx(raw))

    def test_text_is_unchanged_and_in_order(self):
        for name, (raw, fixed) in self.cases.items():
            with self.subTest(name):
                self.assertEqual(texts(document(raw)), texts(document(fixed)))

    def test_no_column_sections_or_column_breaks_left(self):
        for name, (_, fixed) in self.cases.items():
            with self.subTest(name):
                root = document(fixed)
                self.assertEqual(root.xpath("//w:sectPr/w:type[@w:val='nextColumn']", namespaces=NS), [])
                self.assertEqual(root.xpath("//w:sectPr/w:cols[@w:num>1]", namespaces=NS), [])

    def test_no_exact_row_heights(self):
        for name, (_, fixed) in self.cases.items():
            with self.subTest(name):
                self.assertEqual(document(fixed).xpath("//w:trHeight[@w:hRule='exact']", namespaces=NS), [])

    def test_table_grid_matches_cell_widths(self):
        checked = 0
        for name, (_, fixed) in self.cases.items():
            for tbl in document(fixed).iter(f"{{{W}}}tbl"):
                grid = [int(c.get(f"{{{W}}}w")) for c in tbl.findall("w:tblGrid/w:gridCol", NS)]
                for tr in tbl.findall("w:tr", NS):
                    cells = tr.findall("w:tc", NS)
                    if len(cells) != len(grid) or any(c.find("w:tcPr/w:gridSpan", NS) is not None for c in cells):
                        continue
                    widths = [int(c.find("w:tcPr/w:tcW", NS).get(f"{{{W}}}w")) for c in cells]
                    with self.subTest(name):
                        for g, w in zip(grid, widths):
                            self.assertLessEqual(abs(g - w), 80, f"grid {grid} vs cells {widths}")
                    checked += 1
                    break
        self.assertGreater(checked, 0)

    def test_user_report_tables_get_real_column_widths(self):
        _, fixed = self.cases["replica_report_1.pdf"]
        grids = [[int(c.get(f"{{{W}}}w")) for c in t.findall("w:tblGrid/w:gridCol", NS)]
                 for t in document(fixed).iter(f"{{{W}}}tbl")]
        five = [g for g in grids if len(g) == 5]
        self.assertTrue(five, grids)
        self.assertGreater(max(five[-1]) - min(five[-1]), 400, f"columns still equal: {five[-1]}")

    def test_docx_still_opens(self):
        from docx import Document

        for name, (_, fixed) in self.cases.items():
            with self.subTest(name):
                Document(io.BytesIO(fixed))


if __name__ == "__main__":
    unittest.main()
