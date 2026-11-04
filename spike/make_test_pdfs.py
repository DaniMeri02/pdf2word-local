"""Generate synthetic PDFs (no real data) to test pdf2docx conversion quality.

Usage: .venv/bin/python make_test_pdfs.py [output_dir]
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "pdf")
OUT.mkdir(parents=True, exist_ok=True)

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10.5, leading=14, alignment=TA_JUSTIFY)
H1 = ss["Heading1"]
H2 = ss["Heading2"]
RIGHT = ParagraphStyle("right", parent=BODY, alignment=TA_RIGHT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11)

FILLER = (
    "This document is for demonstration purposes only and contains no real data. "
    "Converting a PDF into an editable document must preserve paragraphs, "
    "<b>bold</b>, <i>italic</i> and the overall structure of the text, so that "
    "the user can freely edit the content without rebuilding the layout. "
    "Every line of this text checks that line spacing, indents and "
    "justification are reasonably preserved after conversion."
)


def logo_png(path: Path) -> Path:
    """Create a fake raster logo (PNG) with numpy + OpenCV."""
    img = np.full((160, 480, 3), 255, np.uint8)
    cv2.circle(img, (80, 80), 60, (180, 90, 20), -1)
    cv2.putText(img, "ACME", (160, 105), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (40, 40, 40), 5, cv2.LINE_AA)
    cv2.imwrite(str(path), img)
    return path


def photo_png(path: Path) -> Path:
    """Create a fake 'photo': gradient with shapes."""
    h, w = 300, 450
    y, x = np.mgrid[0:h, 0:w]
    img = np.dstack([(x * 255 / w), (y * 255 / h), np.full((h, w), 160)]).astype(np.uint8)
    cv2.rectangle(img, (60, 60), (200, 220), (30, 30, 200), -1)
    cv2.circle(img, (320, 150), 80, (20, 200, 60), -1)
    cv2.imwrite(str(path), img)
    return path


def chart() -> Drawing:
    d = Drawing(14 * cm, 6 * cm)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 40, 20, 12 * cm, 4.5 * cm
    bc.data = [[12, 18, 9, 22, 15], [8, 11, 14, 10, 19]]
    bc.categoryAxis.categoryNames = ["Jan", "Feb", "Mar", "Apr", "May"]
    bc.bars[0].fillColor = colors.HexColor("#2b6cb0")
    bc.bars[1].fillColor = colors.HexColor("#dd6b20")
    d.add(bc)
    return d


def table(data, widths, header=True, extra=None):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style + (extra or [])))
    return t


# 1. Single-column letter -----------------------------------------------------
def letter(logo: Path):
    doc = SimpleDocTemplate(str(OUT / "1_letter.pdf"), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm)
    s = [
        Image(str(logo), width=5 * cm, height=5 * cm * 160 / 480, hAlign="LEFT"),
        Spacer(1, 0.6 * cm),
        Paragraph("ACME Ltd — 1 Example Street, 00000 Faketown", SMALL),
        Spacer(1, 1 * cm),
        Paragraph("Mr John Example<br/>42 Made-up Road<br/>99999 Testville", RIGHT),
        Spacer(1, 1 * cm),
        Paragraph("Faketown, 4 November 2026", BODY),
        Spacer(1, 0.4 * cm),
        Paragraph("<b>Subject: test letter for conversion</b>", BODY),
        Spacer(1, 0.4 * cm),
        Paragraph("Dear Mr Example,", BODY),
    ]
    for _ in range(4):
        s += [Spacer(1, 0.25 * cm), Paragraph(FILLER, BODY)]
    s += [
        Spacer(1, 0.4 * cm),
        Paragraph("Checklist:", BODY),
        Paragraph("• first item with <u>underlined text</u>;", BODY),
        Paragraph("• second item with <font color='#c53030'>coloured text</font>;", BODY),
        Paragraph("• third item with a number: 1,234.56 €.", BODY),
        Spacer(1, 1 * cm),
        Paragraph("Kind regards,", BODY),
        Spacer(1, 1.2 * cm),
        Paragraph("<i>The Test Manager</i>", RIGHT),
    ]
    doc.build(s)


# 2. Invoice with tables and merged cells -----------------------------------------
def invoice(logo: Path):
    doc = SimpleDocTemplate(str(OUT / "2_invoice.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    w = A4[0] - 4 * cm
    heading = Table(
        [[Image(str(logo), width=4.5 * cm, height=1.5 * cm), Paragraph("<b>INVOICE No. 2026/0042</b><br/>Date: 04/11/2026", RIGHT)]],
        colWidths=[w / 2, w / 2],
    )
    parties = table(
        [
            ["Supplier", "Customer"],
            [Paragraph("ACME Ltd<br/>VAT 00000000000<br/>1 Example Street", SMALL),
             Paragraph("Beta Testing plc<br/>VAT 11111111111<br/>7 Fictional Avenue", SMALL)],
        ],
        [w / 2, w / 2],
    )
    rows = [["Code", "Description", "Qty", "Price", "VAT", "Total"]]
    items = [
        ("A01", "Technical consulting (test)", 3, 120.00),
        ("B07", "Annual demo software licence", 1, 450.00),
        ("C12", "Assorted consumables", 12, 4.75),
        ("D03", "Remote support (hours)", 5, 60.00),
        ("E99", "Shipping and packaging", 1, 25.00),
    ]
    net = 0.0
    for code, desc, q, p in items:
        tot = q * p
        net += tot
        rows.append([code, desc, str(q), f"{p:,.2f}", "22%", f"{tot:,.2f}"])
    vat = net * 0.22
    rows += [
        ["", "", "", "Net", "", f"{net:,.2f}"],
        ["", "", "", "VAT 22%", "", f"{vat:,.2f}"],
        ["", "", "", "TOTAL", "", f"{net + vat:,.2f}"],
    ]
    n = len(rows)
    details = table(
        rows,
        [1.4 * cm, 7.6 * cm, 1.4 * cm, 2.6 * cm, 1.4 * cm, 2.6 * cm],
        extra=[
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            # merged cells: totals labels span two columns
            ("SPAN", (3, n - 3), (4, n - 3)),
            ("SPAN", (3, n - 2), (4, n - 2)),
            ("SPAN", (3, n - 1), (4, n - 1)),
            ("SPAN", (0, n - 3), (2, n - 1)),
            ("FONTNAME", (3, n - 1), (-1, n - 1), "Helvetica-Bold"),
            ("BACKGROUND", (3, n - 1), (-1, n - 1), colors.HexColor("#fefcbf")),
            ("ROWBACKGROUNDS", (0, 1), (-1, n - 4), [colors.white, colors.HexColor("#f7fafc")]),
        ],
    )
    payment = table(
        [["Payment method", "Bank transfer"], ["IBAN", "IT00 X000 0000 0000 0000 0000 000"], ["Due", "30 days from invoice"]],
        [5 * cm, w - 5 * cm],
        header=False,
    )
    doc.build([
        heading, Spacer(1, 0.8 * cm), parties, Spacer(1, 0.8 * cm), details,
        Spacer(1, 0.8 * cm), payment, Spacer(1, 0.8 * cm),
        Paragraph("Document generated for testing. No tax value.", SMALL),
    ])


# 3. Two-column article with image ------------------------------------------------
def two_columns(photo: Path):
    path = OUT / "3_two_columns.pdf"
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    gap = 0.8 * cm
    col_w = (doc.width - gap) / 2
    title_h = 3 * cm
    title = Frame(doc.leftMargin, doc.bottomMargin + doc.height - title_h, doc.width, title_h, id="title")
    c1 = Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height - title_h, id="c1")
    c2 = Frame(doc.leftMargin + col_w + gap, doc.bottomMargin, col_w, doc.height - title_h, id="c2")
    p1 = Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height, id="p1")
    p2 = Frame(doc.leftMargin + col_w + gap, doc.bottomMargin, col_w, doc.height, id="p2")
    doc.addPageTemplates([
        PageTemplate(id="first", frames=[title, c1, c2]),
        PageTemplate(id="others", frames=[p1, p2]),
    ])
    s = [
        Paragraph("Test Newsletter — Autumn Edition", H1),
        Paragraph("<i>An article laid out in two columns to check reading order.</i>", BODY),
        NextPageTemplate("others"),
    ]
    for i in range(1, 7):
        s.append(Paragraph(f"Section {i}", H2))
        s.append(Paragraph(FILLER, BODY))
        if i == 2:
            s += [Spacer(1, 0.2 * cm), Image(str(photo), width=col_w, height=col_w * 300 / 450),
                  Paragraph("<i>Figure 1 — synthetic sample image.</i>", SMALL)]
        if i == 4:
            s += [Spacer(1, 0.2 * cm), column_chart(col_w),
                  Paragraph("<i>Figure 2 — vector chart.</i>", SMALL)]
        s.append(Paragraph(FILLER, BODY))
    doc.build(s)


def column_chart(width):
    d = chart()
    scale = width / d.width
    d.scale(scale, scale)
    d.width *= scale
    d.height *= scale
    return d


# 4. Form with fields and boxes ---------------------------------------------------
def form():
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(OUT / "4_form.pdf"), pagesize=A4)
    W, H = A4
    x0 = 2 * cm
    y = H - 2.5 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x0, y, "REQUEST FORM (TEST)")
    c.setFont("Helvetica", 9)
    c.drawString(x0, y - 14, "Fill in using block capitals. All data is fictitious.")
    y -= 1.5 * cm

    def field(label, x, y, w):
        c.setFont("Helvetica", 9)
        c.drawString(x, y + 14, label)
        c.rect(x, y - 4, w, 16)

    sections = [
        ("1. Personal details", [("Surname", 8), ("First name", 8), ("Tax code", 8), ("Date of birth", 8)]),
        ("2. Address", [("Street", 16.6), ("Postcode", 4), ("Town", 8), ("County", 4)]),
        ("3. Contacts", [("Phone", 8), ("Email", 8)]),
    ]
    for title, fields in sections:
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.rect(x0, y - 4, W - 4 * cm, 16, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0 + 4, y, title)
        y -= 1.1 * cm
        x = x0
        for label, wcm in fields:
            w = wcm * cm
            if x + w > W - 2 * cm + 1:
                x = x0
                y -= 1.2 * cm
            field(label, x, y, w)
            x += w + 0.6 * cm
        y -= 1.6 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "4. Request type (tick one)")
    y -= 0.8 * cm
    c.setFont("Helvetica", 9.5)
    for i, opt in enumerate(["New activation", "Change of details", "Termination", "Other (specify)"]):
        yy = y - i * 0.6 * cm
        c.rect(x0, yy - 2, 9, 9)
        c.drawString(x0 + 16, yy, opt)
    y -= 3.2 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "5. Notes")
    c.rect(x0, y - 4 * cm, W - 4 * cm, 3.6 * cm)
    y -= 5.5 * cm
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Place and date ____________________________")
    c.drawString(W / 2 + 1 * cm, y, "Signature ____________________________")
    c.showPage()
    c.save()


# 5. Long mixed document ------------------------------------------------------
def mixed_long(logo: Path, photo: Path):
    doc = SimpleDocTemplate(str(OUT / "5_mixed_long.pdf"), pagesize=A4)

    def footer(canv, d):
        canv.setFont("Helvetica", 8)
        canv.drawString(2 * cm, 1.2 * cm, "Test report — synthetic document")
        canv.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {d.page}")

    s = [Image(str(logo), width=6 * cm, height=2 * cm), Spacer(1, 2 * cm),
         Paragraph("Technical Test Report", ss["Title"]),
         Paragraph("Long document with mixed content for conversion testing", ss["Heading3"]), PageBreak()]
    for ch in range(1, 8):
        s.append(Paragraph(f"Chapter {ch}", H1))
        for _ in range(3):
            s.append(Paragraph(FILLER, BODY))
            s.append(Spacer(1, 0.2 * cm))
        if ch % 2:
            data = [["Indicator", "Q1", "Q2", "Q3", "Q4"]] + [
                [f"Item {ch}.{r}", *[f"{(ch * r * k) % 97 + 3}.{k}" for k in range(1, 5)]] for r in range(1, 9)
            ]
            s += [table(data, [5 * cm] + [2.6 * cm] * 4), Spacer(1, 0.4 * cm)]
        else:
            s += [Image(str(photo), width=10 * cm, height=6.7 * cm), Spacer(1, 0.3 * cm), chart()]
        for _ in range(3):
            s.append(Paragraph(FILLER, BODY))
        s.append(PageBreak())
    doc.build(s, onFirstPage=footer, onLaterPages=footer)


# 6. Password-protected PDF (only if PyMuPDF is installed) ----------------------
def protected():
    try:
        import pymupdf
    except ImportError:
        return
    with pymupdf.open(OUT / "1_letter.pdf") as d:
        d.save(OUT / "protected_letter.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="test-owner")


if __name__ == "__main__":
    img = OUT / "_img"
    img.mkdir(exist_ok=True)
    logo = logo_png(img / "logo.png")
    photo = photo_png(img / "photo.png")
    letter(logo)
    invoice(logo)
    two_columns(photo)
    form()
    mixed_long(logo, photo)
    protected()
    for p in sorted(OUT.glob("*.pdf")):
        print(p)
