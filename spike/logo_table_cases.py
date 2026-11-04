"""'Logo on top + table below' variants, used to chase extra pages in the DOCX.

None of these reproduced the bug in Word for Mac (see README, "Known issues").
Usage: .venv/bin/python logo_table_cases.py [output_dir]
"""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from make_test_pdfs import BODY, H1, logo_png

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "cases/pdf")
OUT.mkdir(parents=True, exist_ok=True)
LOGO = logo_png(OUT / "logo.png")

STYLES = {
    "grid": [("GRID", (0, 0), (-1, -1), 0.5, colors.grey)],
    "borderless": [],
    "horizontal_rules": [("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.grey)],
    "zebra": [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#dbe7f5")])],
}


def table(rows: int, style=STYLES["grid"]):
    data = [["Date", "Description", "Amount"]] + [
        [f"{(i % 28) + 1:02d}/10/2026", f"Test transaction number {i}", f"{(i * 37) % 900 + 10}.00"] for i in range(rows)
    ]
    t = Table(data, colWidths=[3 * cm, 10 * cm, 3 * cm], repeatRows=1)
    t.setStyle(TableStyle(style + [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    return t


def case(name, content, **margins):
    SimpleDocTemplate(str(OUT / f"{name}.pdf"), pagesize=A4, **margins).build(content)


def logo(w=5 * cm, align="LEFT"):
    return Image(str(LOGO), width=w, height=w * 160 / 480, hAlign=align)


for rows in (8, 25):
    case(f"a_logo_left_table_{rows}", [logo(), Spacer(1, 0.5 * cm), table(rows)])
case("b_logo_center_table_30", [logo(align="CENTER"), Spacer(1, 0.5 * cm), table(30)])
case("c_logo_title_table_30", [logo(), Paragraph("Test account statement", H1), table(30)])
case("d_big_logo_table_25", [logo(w=12 * cm, align="CENTER"), Spacer(1, 0.3 * cm), table(25)])
case("e_logo_text_table_30", [logo(), Paragraph("Holder: John Example — Account no. 0000000", BODY), Spacer(1, 0.3 * cm), table(30)])
# Table filling the page down to the bottom margin (33 rows is the most that fits on one A4 page).
for name, style in STYLES.items():
    case(f"f_full_page_{name}", [logo(), Spacer(1, 0.5 * cm), table(33, style)])

for p in sorted(OUT.glob("*.pdf")):
    print(p)
