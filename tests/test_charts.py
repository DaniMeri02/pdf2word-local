"""Regression tests for python/pdf2word/charts.py (chart detection).

Run: spike/.venv/bin/python -m unittest discover -s tests -p "test_*.py"

Word's PDF export (seen with "Microsoft Word 2016" + ilovepdf) draws table borders
as thin *filled* rectangles with no text inside. They must not be mistaken for the
bars of a chart, otherwise the whole table is rasterized into an image.
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

import pymupdf  # noqa: E402

from pdf2word import convert  # noqa: E402
from pdf2word.charts import find_charts  # noqa: E402

BORDER = 0.5  # pt, like Word's thin table borders


def word_style_table_pdf() -> bytes:
    """One A4 page: logo image, heading text, two tables whose borders are filled rects."""
    doc = pymupdf.open()
    page = doc.new_page(width=595.4, height=841.9)
    # logo (raster image, like the user's 306x58 px logo)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 306, 58), False)
    pix.set_rect(pix.irect, (31, 78, 140))
    page.insert_image(pymupdf.Rect(40, 34.3, 189, 62.5), pixmap=pix)
    page.insert_text((414, 118), "Heading text", fontname="tiro", fontsize=11)

    def table(x0, y0, col_widths, row_h, rows):
        x1 = x0 + sum(col_widths)
        y1 = y0 + row_h * rows
        # One separate filled path per border segment, as in the user's report
        # ("paths": 112, "filled": 112, all "re").
        shape = page.new_shape()
        borders = [pymupdf.Rect(x0, y0 + r * row_h, x1, y0 + r * row_h + BORDER) for r in range(rows + 1)]
        x = x0
        for w in [0, *col_widths]:
            x += w
            borders.append(pymupdf.Rect(x, y0, x + BORDER, y1))
        for b in borders:
            shape.draw_rect(b)
            shape.finish(fill=(0, 0, 0), color=None)
        shape.commit()
        for r in range(rows):
            x = x0
            for c, w in enumerate(col_widths):
                page.insert_text((x + 4, y0 + r * row_h + 14), f"Cell {r}.{c}", fontname="tiro", fontsize=10)
                x += w

    table(42, 102.5, [80, 80, 100, 100, 156], 25, 8)
    table(43, 333, [460, 57], 23.5, 4)
    return doc.tobytes()


def bar_chart_pdf() -> bytes:
    """A real bar chart: filled coloured bars on an axis, short labels below."""
    doc = pymupdf.open()
    page = doc.new_page(width=595.4, height=841.9)
    shape = page.new_shape()
    shape.draw_line((60, 400), (400, 400))  # axis
    shape.finish(color=(0, 0, 0), width=1)
    for i, h in enumerate([80, 120, 60, 150, 100]):
        shape.draw_rect(pymupdf.Rect(80 + i * 60, 400 - h, 120 + i * 60, 400))
        shape.finish(fill=(0.17, 0.42, 0.69), color=None)
    shape.commit()
    for i, label in enumerate(["Jan", "Feb", "Mar", "Apr", "May"]):
        page.insert_text((88 + i * 60, 412), label, fontname="helv", fontsize=8)
    return doc.tobytes()


class ChartDetection(unittest.TestCase):
    def test_word_table_borders_are_not_a_chart(self):
        with pymupdf.open(stream=word_style_table_pdf()) as doc:
            self.assertEqual(find_charts(doc[0]), [])

    def test_bar_chart_is_still_detected(self):
        with pymupdf.open(stream=bar_chart_pdf()) as doc:
            self.assertEqual(len(find_charts(doc[0])), 1)

    def test_word_tables_stay_editable_tables(self):
        docx = convert(word_style_table_pdf())
        xml = zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode()
        self.assertGreaterEqual(xml.count("<w:tbl>"), 2, "tables must be real DOCX tables")
        self.assertIn("Cell 0.0", xml, "table text must stay editable text")


if __name__ == "__main__":
    unittest.main()
