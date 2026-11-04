"""Pre-elaborazione: trasforma i grafici vettoriali "squadrati" in immagini.

pdf2docx rasterizza da solo la grafica vettoriale che contiene curve o diagonali,
ma un grafico a barre è fatto solo di rettangoli e linee orizzontali/verticali:
pdf2docx lo scambia per una tabella e produce una tabella vuota.

Qui, prima della conversione, si individuano questi grafici e si sostituiscono
con un'immagine della stessa area (etichette degli assi comprese).

Euristica per distinguere un grafico da una tabella: nelle tabelle i riempimenti
colorati sono sfondi di celle e contengono testo; nei grafici le barre sono
riempimenti colorati senza testo dentro.
"""

from __future__ import annotations

import pymupdf

# Riempimenti quasi bianchi (es. righe alternate di una tabella) non contano.
SOGLIA_BIANCO = 0.95
# Quanti riempimenti senza testo servono per considerare l'area un grafico.
MIN_RIEMPIMENTI_VUOTI = 3
# Distanza massima (pt) entro cui le etichette degli assi vengono inglobate.
MARGINE_ETICHETTE = 14.0
# Un'etichetta d'asse è corta: più stretta di questa frazione del grafico.
LARGHEZZA_MAX_ETICHETTA = 0.5
# Risoluzione dell'immagine che sostituisce il grafico.
DPI = 200


def _quasi_bianco(colore) -> bool:
    return colore is None or all(c >= SOGLIA_BIANCO for c in colore)


def _solo_rettangoli(disegno: dict) -> bool:
    return all(item[0] in ("re", "qu") for item in disegno["items"])


def _righe_di_testo(pagina: pymupdf.Page) -> list[pymupdf.Rect]:
    righe = []
    for blocco in pagina.get_text("dict")["blocks"]:
        for riga in blocco.get("lines", []):
            if any(s["text"].strip() for s in riga["spans"]):
                righe.append(pymupdf.Rect(riga["bbox"]))
    return righe


def _contiene_testo(area: pymupdf.Rect, righe: list[pymupdf.Rect]) -> bool:
    interno = area + (1, 1, -1, -1)
    return any(interno.intersects(r) for r in righe)


def trova_grafici(pagina: pymupdf.Page) -> list[pymupdf.Rect]:
    """Restituisce le aree della pagina che contengono grafici a barre o simili."""
    disegni = pagina.get_drawings()
    if not disegni:
        return []
    righe = _righe_di_testo(pagina)
    aree = []
    for gruppo in pagina.cluster_drawings(drawings=disegni):
        dentro = [d for d in disegni if gruppo.contains(d["rect"])]
        vuoti = [
            d for d in dentro
            if d.get("fill") is not None
            and not _quasi_bianco(d["fill"])
            and _solo_rettangoli(d)
            and not _contiene_testo(d["rect"], righe)
        ]
        if len(vuoti) < MIN_RIEMPIMENTI_VUOTI:
            continue
        # Ingloba le etichette degli assi: righe corte, vicine e interamente
        # dentro l'area allargata.
        allargata = gruppo + (-MARGINE_ETICHETTE, -MARGINE_ETICHETTE, MARGINE_ETICHETTE, MARGINE_ETICHETTE)
        area = pymupdf.Rect(gruppo)
        for r in righe:
            if allargata.contains(r) and r.width <= LARGHEZZA_MAX_ETICHETTA * gruppo.width:
                area |= r
        aree.append(area)
    return aree


def rasterizza_grafici(doc: pymupdf.Document) -> int:
    """Sostituisce, pagina per pagina, ogni grafico trovato con la sua immagine.

    Modifica ``doc`` in memoria. Restituisce il numero di grafici sostituiti.
    """
    totale = 0
    for pagina in doc:
        aree = trova_grafici(pagina)
        if not aree:
            continue
        immagini = [pagina.get_pixmap(clip=a, dpi=DPI) for a in aree]
        for a in aree:
            pagina.add_redact_annot(a, fill=False, cross_out=False)
        pagina.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        for a, pix in zip(aree, immagini):
            pagina.insert_image(a, pixmap=pix)
        totale += len(aree)
    return totale
