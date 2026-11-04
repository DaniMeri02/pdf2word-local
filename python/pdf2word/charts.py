"""Pre-processing: turn axis-aligned vector charts into images.

pdf2docx already rasterizes vector graphics that contain curves or diagonals,
but a bar chart is made only of rectangles and horizontal/vertical lines:
pdf2docx mistakes it for a table and outputs an empty table.

Before conversion, these charts are detected and replaced with an image of the
same area (axis labels included).

Heuristic to tell a chart from a table: in tables, coloured fills are cell
backgrounds and contain text; in charts, bars are coloured fills with no text.
Thin filled rectangles are lines, not bars: Word's PDF export draws table borders
that way, and counting them as bars turned whole tables into images.
"""

from __future__ import annotations

import pymupdf

# Near-white fills (e.g. zebra-striped table rows) do not count.
WHITE_THRESHOLD = 0.95
# How many text-free fills are needed to treat an area as a chart.
MIN_EMPTY_FILLS = 3
# A filled rectangle thinner than this (pt) is a line (e.g. a table border), not a bar.
MIN_BAR_THICKNESS = 2.0
# Max distance (pt) within which axis labels are absorbed into the chart.
LABEL_MARGIN = 14.0
# An axis label is short: narrower than this fraction of the chart.
MAX_LABEL_WIDTH = 0.5
# Resolution of the image that replaces the chart.
DPI = 200


def _near_white(color) -> bool:
    return color is None or all(c >= WHITE_THRESHOLD for c in color)


def _rects_only(drawing: dict) -> bool:
    return all(item[0] in ("re", "qu") for item in drawing["items"])


def _text_lines(page: pymupdf.Page) -> list[pymupdf.Rect]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if any(s["text"].strip() for s in line["spans"]):
                lines.append(pymupdf.Rect(line["bbox"]))
    return lines


def _is_bar(rect: pymupdf.Rect) -> bool:
    return min(rect.width, rect.height) >= MIN_BAR_THICKNESS


def _contains_text(area: pymupdf.Rect, lines: list[pymupdf.Rect]) -> bool:
    inner = area + (1, 1, -1, -1)
    return any(inner.intersects(r) for r in lines)


def find_charts(page: pymupdf.Page) -> list[pymupdf.Rect]:
    """Return the page areas that contain bar charts or similar."""
    drawings = page.get_drawings()
    if not drawings:
        return []
    lines = _text_lines(page)
    areas = []
    for cluster in page.cluster_drawings(drawings=drawings):
        inside = [d for d in drawings if cluster.contains(d["rect"])]
        empty = [
            d for d in inside
            if d.get("fill") is not None
            and not _near_white(d["fill"])
            and _rects_only(d)
            and _is_bar(d["rect"])
            and not _contains_text(d["rect"], lines)
        ]
        if len(empty) < MIN_EMPTY_FILLS:
            continue
        # Absorb axis labels: short lines, close by, fully inside the grown area.
        grown = cluster + (-LABEL_MARGIN, -LABEL_MARGIN, LABEL_MARGIN, LABEL_MARGIN)
        area = pymupdf.Rect(cluster)
        for r in lines:
            if grown.contains(r) and r.width <= MAX_LABEL_WIDTH * cluster.width:
                area |= r
        areas.append(area)
    return areas


def rasterize_charts(doc: pymupdf.Document) -> int:
    """Replace, page by page, every chart found with its image.

    Modifies ``doc`` in memory. Returns the number of charts replaced.
    """
    total = 0
    for page in doc:
        areas = find_charts(page)
        if not areas:
            continue
        images = [page.get_pixmap(clip=a, dpi=DPI) for a in areas]
        for a in areas:
            page.add_redact_annot(a, fill=False, cross_out=False)
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        for a, pix in zip(areas, images):
            page.insert_image(a, pixmap=pix)
        total += len(areas)
    return total
