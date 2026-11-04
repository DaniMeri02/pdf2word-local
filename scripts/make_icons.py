"""Generate the PWA's PNG icons (web/icons/) by drawing them with PyMuPDF.

Usage: python scripts/make_icons.py   (needs pymupdf, e.g. from spike/'s venv)
"""

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent.parent / "web" / "icons"
BLUE = (0x1F / 255, 0x4E / 255, 0x8C / 255)
WHITE = (1, 1, 1)
LIGHT_BLUE = (0.80, 0.87, 0.96)


def draw(side: int, maskable: bool) -> pymupdf.Pixmap:
    doc = pymupdf.open()
    p = doc.new_page(width=100, height=100)
    s = p.new_shape()
    if maskable:
        s.draw_rect(p.rect)  # full bleed: Android crops the shape
    else:
        s.draw_rect(pymupdf.Rect(4, 4, 96, 96), radius=0.22)
    s.finish(fill=BLUE, color=None)
    # Sheet with folded corner; in the maskable variant it stays in the safe zone (80%).
    k = 0.72 if maskable else 1.0

    def pt(x, y):
        return pymupdf.Point(50 + (x - 50) * k, 50 + (y - 50) * k)

    s.draw_polyline([pt(28, 18), pt(62, 18), pt(74, 30), pt(74, 82), pt(28, 82), pt(28, 18)])
    s.finish(fill=WHITE, color=None, closePath=True)
    s.draw_polyline([pt(62, 18), pt(62, 30), pt(74, 30)])
    s.finish(fill=LIGHT_BLUE, color=None, closePath=True)
    # Lines of editable text
    for y, x1 in ((42, 66), (51, 66), (60, 58)):
        s.draw_line(pt(36, y), pt(x1, y))
        s.finish(color=BLUE, width=4 * k, lineCap=1, closePath=False)
    # Text cursor at the end of the last line
    s.draw_line(pt(63, 55), pt(63, 70))
    s.finish(color=BLUE, width=3 * k, lineCap=1, closePath=False)
    s.commit()
    return p.get_pixmap(matrix=pymupdf.Matrix(side / 100, side / 100), alpha=not maskable)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, False).save(OUT / "icon-192.png")
    draw(512, False).save(OUT / "icon-512.png")
    draw(512, True).save(OUT / "icon-maskable-512.png")
    for f in sorted(OUT.glob("*.png")):
        print(f)
