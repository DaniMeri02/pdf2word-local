"""Genera PDF sintetici (nessun dato reale) per testare la qualità di pdf2docx.

Uso: .venv/bin/python genera_pdf.py [cartella_output]
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

LOREM = (
    "Il presente documento ha finalità puramente dimostrative e non contiene dati reali. "
    "La conversione da PDF a documento modificabile deve preservare paragrafi, "
    "<b>grassetto</b>, <i>corsivo</i> e la struttura generale del testo, così che "
    "l'utente possa intervenire liberamente sul contenuto senza ricomporre l'impaginazione. "
    "Ogni riga di questo testo serve a verificare che l'interlinea, i rientri e la "
    "giustificazione siano mantenuti in modo ragionevole dopo la conversione."
)


def logo_png(path: Path) -> Path:
    """Crea un logo raster finto (PNG) con numpy + OpenCV."""
    img = np.full((160, 480, 3), 255, np.uint8)
    cv2.circle(img, (80, 80), 60, (180, 90, 20), -1)
    cv2.putText(img, "ACME", (160, 105), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (40, 40, 40), 5, cv2.LINE_AA)
    cv2.imwrite(str(path), img)
    return path


def foto_png(path: Path) -> Path:
    """Crea una 'foto' finta: gradiente con forme."""
    h, w = 300, 450
    y, x = np.mgrid[0:h, 0:w]
    img = np.dstack([(x * 255 / w), (y * 255 / h), np.full((h, w), 160)]).astype(np.uint8)
    cv2.rectangle(img, (60, 60), (200, 220), (30, 30, 200), -1)
    cv2.circle(img, (320, 150), 80, (20, 200, 60), -1)
    cv2.imwrite(str(path), img)
    return path


def grafico() -> Drawing:
    d = Drawing(14 * cm, 6 * cm)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 40, 20, 12 * cm, 4.5 * cm
    bc.data = [[12, 18, 9, 22, 15], [8, 11, 14, 10, 19]]
    bc.categoryAxis.categoryNames = ["Gen", "Feb", "Mar", "Apr", "Mag"]
    bc.bars[0].fillColor = colors.HexColor("#2b6cb0")
    bc.bars[1].fillColor = colors.HexColor("#dd6b20")
    d.add(bc)
    return d


def tabella(dati, larghezze, intestazione=True, extra=None):
    t = Table(dati, colWidths=larghezze, repeatRows=1 if intestazione else 0)
    stile = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if intestazione:
        stile += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(stile + (extra or [])))
    return t


# 1. Lettera a una colonna -----------------------------------------------------
def lettera(logo: Path):
    doc = SimpleDocTemplate(str(OUT / "1_lettera.pdf"), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm)
    s = [
        Image(str(logo), width=5 * cm, height=5 * cm * 160 / 480, hAlign="LEFT"),
        Spacer(1, 0.6 * cm),
        Paragraph("ACME S.r.l. — Via degli Esempi 1, 00000 Cittàfinta", SMALL),
        Spacer(1, 1 * cm),
        Paragraph("Spett.le<br/>Mario Esempio<br/>Via Inventata 42<br/>99999 Paese di Prova", RIGHT),
        Spacer(1, 1 * cm),
        Paragraph("Cittàfinta, 4 novembre 2026", BODY),
        Spacer(1, 0.4 * cm),
        Paragraph("<b>Oggetto: comunicazione di prova per test di conversione</b>", BODY),
        Spacer(1, 0.4 * cm),
        Paragraph("Gentile Sig. Esempio,", BODY),
    ]
    for _ in range(4):
        s += [Spacer(1, 0.25 * cm), Paragraph(LOREM, BODY)]
    s += [
        Spacer(1, 0.4 * cm),
        Paragraph("Elenco puntato di verifica:", BODY),
        Paragraph("• primo punto con <u>testo sottolineato</u>;", BODY),
        Paragraph("• secondo punto con <font color='#c53030'>testo colorato</font>;", BODY),
        Paragraph("• terzo punto con un numero: 1.234,56 €.", BODY),
        Spacer(1, 1 * cm),
        Paragraph("Cordiali saluti,", BODY),
        Spacer(1, 1.2 * cm),
        Paragraph("<i>Il Responsabile di Prova</i>", RIGHT),
    ]
    doc.build(s)


# 2. Fattura con tabelle e celle unite -------------------------------------------
def fattura(logo: Path):
    doc = SimpleDocTemplate(str(OUT / "2_fattura.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    w = A4[0] - 4 * cm
    testata = Table(
        [[Image(str(logo), width=4.5 * cm, height=1.5 * cm), Paragraph("<b>FATTURA N. 2026/0042</b><br/>Data: 04/11/2026", RIGHT)]],
        colWidths=[w / 2, w / 2],
    )
    anagrafiche = tabella(
        [
            ["Fornitore", "Cliente"],
            [Paragraph("ACME S.r.l.<br/>P.IVA 00000000000<br/>Via degli Esempi 1", SMALL),
             Paragraph("Beta Prove S.p.A.<br/>P.IVA 11111111111<br/>Corso Fittizio 7", SMALL)],
        ],
        [w / 2, w / 2],
    )
    righe = [["Cod.", "Descrizione", "Q.tà", "Prezzo", "IVA", "Totale"]]
    voci = [
        ("A01", "Consulenza tecnica di prova", 3, 120.00),
        ("B07", "Licenza software dimostrativa annuale", 1, 450.00),
        ("C12", "Materiale di consumo assortito", 12, 4.75),
        ("D03", "Assistenza remota (ore)", 5, 60.00),
        ("E99", "Trasporto e imballo", 1, 25.00),
    ]
    imponibile = 0.0
    for cod, desc, q, p in voci:
        tot = q * p
        imponibile += tot
        righe.append([cod, desc, str(q), f"{p:,.2f}", "22%", f"{tot:,.2f}"])
    iva = imponibile * 0.22
    righe += [
        ["", "", "", "Imponibile", "", f"{imponibile:,.2f}"],
        ["", "", "", "IVA 22%", "", f"{iva:,.2f}"],
        ["", "", "", "TOTALE", "", f"{imponibile + iva:,.2f}"],
    ]
    n = len(righe)
    dettaglio = tabella(
        righe,
        [1.4 * cm, 7.6 * cm, 1.4 * cm, 2.6 * cm, 1.4 * cm, 2.6 * cm],
        extra=[
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            # celle unite: etichette dei totali su due colonne
            ("SPAN", (3, n - 3), (4, n - 3)),
            ("SPAN", (3, n - 2), (4, n - 2)),
            ("SPAN", (3, n - 1), (4, n - 1)),
            ("SPAN", (0, n - 3), (2, n - 1)),
            ("FONTNAME", (3, n - 1), (-1, n - 1), "Helvetica-Bold"),
            ("BACKGROUND", (3, n - 1), (-1, n - 1), colors.HexColor("#fefcbf")),
            ("ROWBACKGROUNDS", (0, 1), (-1, n - 4), [colors.white, colors.HexColor("#f7fafc")]),
        ],
    )
    pagamento = tabella(
        [["Modalità di pagamento", "Bonifico bancario"], ["IBAN", "IT00 X000 0000 0000 0000 0000 000"], ["Scadenza", "30 gg d.f."]],
        [5 * cm, w - 5 * cm],
        intestazione=False,
    )
    doc.build([
        testata, Spacer(1, 0.8 * cm), anagrafiche, Spacer(1, 0.8 * cm), dettaglio,
        Spacer(1, 0.8 * cm), pagamento, Spacer(1, 0.8 * cm),
        Paragraph("Documento generato a scopo di test. Nessun valore fiscale.", SMALL),
    ])


# 3. Articolo a due colonne con immagine ------------------------------------------
def due_colonne(foto: Path):
    path = OUT / "3_due_colonne.pdf"
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    gap = 0.8 * cm
    col_w = (doc.width - gap) / 2
    titolo_h = 3 * cm
    titolo = Frame(doc.leftMargin, doc.bottomMargin + doc.height - titolo_h, doc.width, titolo_h, id="titolo")
    c1 = Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height - titolo_h, id="c1")
    c2 = Frame(doc.leftMargin + col_w + gap, doc.bottomMargin, col_w, doc.height - titolo_h, id="c2")
    p1 = Frame(doc.leftMargin, doc.bottomMargin, col_w, doc.height, id="p1")
    p2 = Frame(doc.leftMargin + col_w + gap, doc.bottomMargin, col_w, doc.height, id="p2")
    doc.addPageTemplates([
        PageTemplate(id="prima", frames=[titolo, c1, c2]),
        PageTemplate(id="altre", frames=[p1, p2]),
    ])
    s = [
        Paragraph("Notiziario di Prova — Edizione Autunno", H1),
        Paragraph("<i>Un articolo impaginato su due colonne per verificare l'ordine di lettura.</i>", BODY),
        NextPageTemplate("altre"),
    ]
    for i in range(1, 7):
        s.append(Paragraph(f"Sezione {i}", H2))
        s.append(Paragraph(LOREM, BODY))
        if i == 2:
            s += [Spacer(1, 0.2 * cm), Image(str(foto), width=col_w, height=col_w * 300 / 450),
                  Paragraph("<i>Figura 1 — immagine sintetica di esempio.</i>", SMALL)]
        if i == 4:
            s += [Spacer(1, 0.2 * cm), grafico_col(col_w),
                  Paragraph("<i>Figura 2 — grafico vettoriale.</i>", SMALL)]
        s.append(Paragraph(LOREM, BODY))
    doc.build(s)


def grafico_col(width):
    d = grafico()
    scala = width / d.width
    d.scale(scala, scala)
    d.width *= scala
    d.height *= scala
    return d


# 4. Modulo con campi e riquadri -------------------------------------------------
def modulo():
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(OUT / "4_modulo.pdf"), pagesize=A4)
    W, H = A4
    x0 = 2 * cm
    y = H - 2.5 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x0, y, "MODULO DI RICHIESTA (DI PROVA)")
    c.setFont("Helvetica", 9)
    c.drawString(x0, y - 14, "Compilare in stampatello. Tutti i dati sono fittizi.")
    y -= 1.5 * cm

    def campo(etichetta, x, y, w):
        c.setFont("Helvetica", 9)
        c.drawString(x, y + 14, etichetta)
        c.rect(x, y - 4, w, 16)

    sezioni = [
        ("1. Dati anagrafici", [("Cognome", 8), ("Nome", 8), ("Codice fiscale", 8), ("Data di nascita", 8)]),
        ("2. Residenza", [("Indirizzo", 16.6), ("CAP", 4), ("Comune", 8), ("Provincia", 4)]),
        ("3. Recapiti", [("Telefono", 8), ("E-mail", 8)]),
    ]
    for titolo, campi in sezioni:
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.rect(x0, y - 4, W - 4 * cm, 16, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0 + 4, y, titolo)
        y -= 1.1 * cm
        x = x0
        for etichetta, wcm in campi:
            w = wcm * cm
            if x + w > W - 2 * cm + 1:
                x = x0
                y -= 1.2 * cm
            campo(etichetta, x, y, w)
            x += w + 0.6 * cm
        y -= 1.6 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "4. Tipo di richiesta (barrare)")
    y -= 0.8 * cm
    c.setFont("Helvetica", 9.5)
    for i, opz in enumerate(["Nuova attivazione", "Modifica dati", "Cessazione", "Altro (specificare)"]):
        yy = y - i * 0.6 * cm
        c.rect(x0, yy - 2, 9, 9)
        c.drawString(x0 + 16, yy, opz)
    y -= 3.2 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "5. Note")
    c.rect(x0, y - 4 * cm, W - 4 * cm, 3.6 * cm)
    y -= 5.5 * cm
    c.setFont("Helvetica", 9)
    c.drawString(x0, y, "Luogo e data ____________________________")
    c.drawString(W / 2 + 1 * cm, y, "Firma ____________________________")
    c.showPage()
    c.save()


# 5. Documento misto di 15 pagine ----------------------------------------------
def misto(logo: Path, foto: Path):
    doc = SimpleDocTemplate(str(OUT / "5_misto_lungo.pdf"), pagesize=A4)

    def piede(canv, d):
        canv.setFont("Helvetica", 8)
        canv.drawString(2 * cm, 1.2 * cm, "Relazione di prova — documento sintetico")
        canv.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Pagina {d.page}")

    s = [Image(str(logo), width=6 * cm, height=2 * cm), Spacer(1, 2 * cm),
         Paragraph("Relazione Tecnica di Prova", ss["Title"]),
         Paragraph("Documento lungo con contenuti misti per test di conversione", ss["Heading3"]), PageBreak()]
    for cap in range(1, 8):
        s.append(Paragraph(f"Capitolo {cap}", H1))
        for _ in range(3):
            s.append(Paragraph(LOREM, BODY))
            s.append(Spacer(1, 0.2 * cm))
        if cap % 2:
            dati = [["Indicatore", "T1", "T2", "T3", "T4"]] + [
                [f"Voce {cap}.{r}", *[f"{(cap * r * k) % 97 + 3},{k}" for k in range(1, 5)]] for r in range(1, 9)
            ]
            s += [tabella(dati, [5 * cm] + [2.6 * cm] * 4), Spacer(1, 0.4 * cm)]
        else:
            s += [Image(str(foto), width=10 * cm, height=6.7 * cm), Spacer(1, 0.3 * cm), grafico()]
        for _ in range(3):
            s.append(Paragraph(LOREM, BODY))
        s.append(PageBreak())
    doc.build(s, onFirstPage=piede, onLaterPages=piede)


# 6. PDF protetto da password (solo se PyMuPDF è installato) ------------------
def protetto():
    try:
        import pymupdf
    except ImportError:
        return
    with pymupdf.open(OUT / "1_lettera.pdf") as d:
        d.save(OUT / "protetto_lettera.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="prova", owner_pw="prova-owner")


if __name__ == "__main__":
    img = OUT / "_img"
    img.mkdir(exist_ok=True)
    logo = logo_png(img / "logo.png")
    foto = foto_png(img / "foto.png")
    lettera(logo)
    fattura(logo)
    due_colonne(foto)
    modulo()
    misto(logo, foto)
    protetto()
    for p in sorted(OUT.glob("*.pdf")):
        print(p)
