"""Synthetic replica of the PDF behind the first user diagnostic report.

Geometry comes from the report (Word 2016 + ilovepdf, A4, Times New Roman,
logo 306x58 px at top-left, two tables whose borders are 112 thin filled
rectangles). Text is filler with roughly the same character counts.

Usage: .venv/bin/python replica_report_1.py [output.pdf]
"""

import sys
from pathlib import Path

import pymupdf

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "cases/replica_report_1.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open()
page = doc.new_page(width=595.4, height=841.9)

# Logo: raster image at the report's position and pixel size.
pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 306, 58), False)
pix.set_rect(pix.irect, (31, 78, 140))
page.insert_image(pymupdf.Rect(40.0, 34.3, 189.0, 62.5), pixmap=pix)


def text(x, y, s, size=10.1, right=None):
    """Insert one line; if right is given, right-align the line at that x."""
    if right is not None:
        x = right - pymupdf.get_text_length(s, fontname="tiro", fontsize=size)
    page.insert_text((x, y), s, fontname="tiro", fontsize=size)


# Header block: lines to the right of the logo and right-aligned lines below it.
text(226, 34, "Company Name Ltd - Registered office 1 Example Street")
text(226, 46, "00000 Faketown (XX) - VAT 00000000000")
text(226, 58, "Phone 000 0000000 - info@example.invalid")
for i, s in enumerate(["Tax code 00000000000", "Share capital 10,000.00", "Register no. 000000", "PEC example@pec.invalid"]):
    text(0, 70 + i * 10.5, s, right=554.5)

# Table borders: separate thin filled rectangles (Word's PDF export style).
BORDER = 0.5


def borders(rows_y, segments):
    """rows_y: horizontal line y's; segments: per row band, list of vertical x's."""
    x0, x1 = min(min(s) for s in segments), max(max(s) for s in segments)
    rects = [pymupdf.Rect(x0, y, x1, y + BORDER) for y in rows_y]
    for (ya, yb), xs in zip(zip(rows_y, rows_y[1:]), segments):
        rects += [pymupdf.Rect(x, ya, x + BORDER, yb) for x in xs]
    shape = page.new_shape()
    for r in rects:
        shape.draw_rect(r)
        shape.finish(fill=(0, 0, 0), color=None)
    shape.commit()


# Table 1: rows 79.1 / 55.0 / 67.0 pt; row 1 = 4-col span + 1, row 2 = 5 cells, row 3 = 2-col span + 3.
X = [42.0, 121.5, 200.7, 303.7, 406.7, 558.2]
Y1 = [102.5, 181.6, 236.6, 303.6]
borders(Y1, [[X[0], X[4], X[5]], X, [X[0], X[2], X[3], X[4], X[5]]])
text(414.4, 116, "Customer name surname", size=11)
for i, s in enumerate(["Street address 12", "00000 Faketown", "Province XX", "Country", "Code 0000"]):
    text(414.4, 133 + i * 11, s)
for x, (a, b) in zip([49.7, 129.2, 208.4, 311.4, 414.4],
                     [("Date", "01/01/2026"), ("Document no.", "0000000000/2026"), ("Customer code", "000000000"),
                      ("Reference", "ABC123"), ("Payment terms", "30 days invoice")]):
    text(x, 195, a, size=11)
    text(x, 211, b)
text(48.7, 247, "Payment method info", size=11)
for i, s in enumerate(["Bank transfer to IBAN", "IT00X0000000000000000", "Bank of Example"]):
    text(48.7, 268 + i * 11, s)
for i, s in enumerate(["Notes line one", "notes line two text", "notes line three", "notes four"]):
    text(208.4, 250 + i * 11, s)

# Table 2: rows 40.1 / 26.5 / 26.3 pt.
X2 = [43.0, 121.5, 200.7, 303.7, 497.0, 560.4]
Y2 = [333.0, 373.1, 399.6, 425.9]
borders(Y2, [X2, X2, [X2[0], X2[2], X2[4], X2[5]]])
for i, s in enumerate(["Description of goods", "or services provided", "in the period", "line four", "five"]):
    text(49.7, 346 + i * 4.5, s, size=11) if i < 2 else None
text(505.4, 349, "Amount", size=11)
text(505.4, 361, "0.00", size=11)
for i, s in enumerate(["Taxable", "VAT", "Total", "Paid", "Due"]):
    text(87.4 + i * 95, 388, s)
text(426.9, 414, "Total due 0.00", size=11)

doc.save(OUT)
print(OUT)
