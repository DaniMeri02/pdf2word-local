"""Genera le icone PNG della PWA (web/icone/) disegnandole con PyMuPDF.

Uso: python scripts/genera_icone.py   (serve pymupdf, es. dal venv di spike/)
"""

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent.parent / "web" / "icone"
BLU = (0x1F / 255, 0x4E / 255, 0x8C / 255)
BIANCO = (1, 1, 1)
AZZURRO = (0.80, 0.87, 0.96)


def disegna(lato: int, maschera: bool) -> pymupdf.Pixmap:
    doc = pymupdf.open()
    p = doc.new_page(width=100, height=100)
    s = p.new_shape()
    if maschera:
        s.draw_rect(p.rect)  # a tutta area: Android ritaglia la forma
    else:
        s.draw_rect(pymupdf.Rect(4, 4, 96, 96), radius=0.22)
    s.finish(fill=BLU, color=None)
    # Foglio con angolo piegato; nella variante maschera sta nella zona sicura (80%).
    k = 0.72 if maschera else 1.0
    def pt(x, y):
        return pymupdf.Point(50 + (x - 50) * k, 50 + (y - 50) * k)
    s.draw_polyline([pt(28, 18), pt(62, 18), pt(74, 30), pt(74, 82), pt(28, 82), pt(28, 18)])
    s.finish(fill=BIANCO, color=None, closePath=True)
    s.draw_polyline([pt(62, 18), pt(62, 30), pt(74, 30)])
    s.finish(fill=AZZURRO, color=None, closePath=True)
    # Righe di testo modificabile
    for y, x1 in ((42, 66), (51, 66), (60, 58)):
        s.draw_line(pt(36, y), pt(x1, y))
        s.finish(color=BLU, width=4 * k, lineCap=1, closePath=False)
    # Cursore di modifica a fine ultima riga
    s.draw_line(pt(63, 55), pt(63, 70))
    s.finish(color=BLU, width=3 * k, lineCap=1, closePath=False)
    s.commit()
    return p.get_pixmap(matrix=pymupdf.Matrix(lato / 100, lato / 100), alpha=not maschera)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    disegna(192, False).save(OUT / "icona-192.png")
    disegna(512, False).save(OUT / "icona-512.png")
    disegna(512, True).save(OUT / "icona-maschera-512.png")
    for f in sorted(OUT.glob("*.png")):
        print(f)
