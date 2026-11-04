"""Privacy-safe diagnostic report of a conversion: layout only, no content.

The report describes the source PDF and the generated DOCX with geometry and
formatting data (page sizes, positions, font names and sizes, table shapes,
section settings). It never includes text, image pixels, link targets or
metadata other than the producing software, so the user can share it to help
reproduce a layout bug without sharing the document.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Optional

import pymupdf
from lxml import etree

# Keep the report short enough to paste in a chat.
MAX_PAGES = 3
MAX_BLOCKS_PER_PAGE = 60
MAX_BODY_ITEMS = 120

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS = {"w": W, "wp": WP}
EMU_PER_PT = 12700


def _r(v: float) -> float:
    return round(float(v), 1)


def _box(rect) -> list[float]:
    return [_r(c) for c in rect]


# --- PDF ------------------------------------------------------------------------

def _pdf_page(page: pymupdf.Page) -> dict[str, Any]:
    from .charts import find_charts

    blocks = []
    for b in page.get_text("dict")["blocks"][:MAX_BLOCKS_PER_PAGE]:
        if b["type"] == 0:
            spans = [s for line in b["lines"] for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            blocks.append({
                "kind": "text",
                "bbox": _box(b["bbox"]),
                "lines": len(b["lines"]),
                "chars": sum(len(s["text"]) for s in spans),
                "fonts": sorted({s["font"] for s in spans}),
                "sizes": sorted({_r(s["size"]) for s in spans}),
            })
        elif b["type"] == 1:
            blocks.append({"kind": "image", "bbox": _box(b["bbox"]), "px": [b.get("width"), b.get("height")]})

    drawings = page.get_drawings()
    ops = {"re": 0, "l": 0, "c": 0, "qu": 0}
    filled = 0
    for d in drawings:
        if d.get("fill") is not None:
            filled += 1
        for item in d["items"]:
            ops[item[0]] = ops.get(item[0], 0) + 1
    clusters = page.cluster_drawings(drawings=drawings) if drawings else []

    return {
        "size": [_r(page.rect.width), _r(page.rect.height)],
        "mediabox": _box(page.mediabox),
        "cropbox": _box(page.cropbox),
        "rotation": page.rotation,
        # get_fonts(): (xref, ext, type, basefont, ...); ext is "n/a" when the font is not embedded
        "fonts": sorted({f"{f[3]} ({f[2]}{', embedded' if f[1] != 'n/a' else ''})" for f in page.get_fonts()}),
        "blocks": blocks,
        "images": [{"bbox": _box(i["bbox"]), "px": [i["width"], i["height"]]} for i in page.get_image_info()],
        "drawings": {"paths": len(drawings), "filled": filled, "ops": ops,
                     "clusters": [_box(c) for c in clusters[:20]]},
        "charts_rasterized": [_box(a) for a in find_charts(page)],
    }


def _pdf_report(pdf: bytes, password: Optional[str]) -> dict[str, Any]:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    if doc.needs_pass:
        doc.authenticate(password or "")
    meta = doc.metadata or {}
    out = {
        "pages": doc.page_count,
        "producer": meta.get("producer") or None,
        "creator": meta.get("creator") or None,
        "encrypted": bool(doc.is_encrypted or meta.get("encryption")),
        "page_details": [_pdf_page(doc[i]) for i in range(min(doc.page_count, MAX_PAGES))],
    }
    doc.close()
    return out


# --- DOCX -----------------------------------------------------------------------

def _w(el, name: str) -> Optional[str]:
    return el.get(f"{{{W}}}{name}") if el is not None else None


def _tw(v: Optional[str]) -> Optional[float]:
    """twips (1/20 pt) -> pt"""
    return _r(int(v) / 20) if v not in (None, "") and v.lstrip("-").isdigit() else None


def _section(sect) -> dict[str, Any]:
    size = sect.find("w:pgSz", NS)
    mar = sect.find("w:pgMar", NS)
    cols = sect.find("w:cols", NS)
    kind = sect.find("w:type", NS)
    return {
        "type": _w(kind, "val") or "nextPage",
        "page": [_tw(_w(size, "w")), _tw(_w(size, "h"))],
        "margins": {k: _tw(_w(mar, k)) for k in ("top", "bottom", "left", "right", "header", "footer")} if mar is not None else None,
        "columns": int(_w(cols, "num") or 1),
        "column_space": _tw(_w(cols, "space")),
    }


def _drawings(el) -> list[dict[str, Any]]:
    out = []
    for kind in ("inline", "anchor"):
        for d in el.iter(f"{{{WP}}}{kind}"):
            ext = d.find("wp:extent", NS)
            item = {"kind": kind}
            if ext is not None:
                item["size"] = [_r(int(ext.get("cx")) / EMU_PER_PT), _r(int(ext.get("cy")) / EMU_PER_PT)]
            if kind == "anchor":
                for axis in ("positionH", "positionV"):
                    p = d.find(f"wp:{axis}", NS)
                    off = p.find("wp:posOffset", NS) if p is not None else None
                    if p is not None:
                        item[axis] = {"from": p.get("relativeFrom"),
                                      "offset": _r(int(off.text) / EMU_PER_PT) if off is not None else None}
                item["behind_text"] = d.get("behindDoc") == "1"
            out.append(item)
    return out


def _runs(el) -> dict[str, Any]:
    fonts, sizes, chars = set(), set(), 0
    for r in el.iter(f"{{{W}}}r"):
        rf = r.find("w:rPr/w:rFonts", NS)
        if rf is not None:
            fonts.update(v for v in (_w(rf, "ascii"), _w(rf, "hAnsi"), _w(rf, "eastAsia")) if v)
        sz = r.find("w:rPr/w:sz", NS)
        if sz is not None and (_w(sz, "val") or "").isdigit():
            sizes.add(int(_w(sz, "val")) / 2)
        chars += sum(len(t.text or "") for t in r.iter(f"{{{W}}}t"))
    return {"fonts": sorted(fonts), "sizes": sorted(sizes), "chars": chars}


def _paragraph(p) -> dict[str, Any]:
    ppr = p.find("w:pPr", NS)
    sp = ppr.find("w:spacing", NS) if ppr is not None else None
    ind = ppr.find("w:ind", NS) if ppr is not None else None
    jc = ppr.find("w:jc", NS) if ppr is not None else None
    item: dict[str, Any] = {"kind": "p", **_runs(p)}
    if sp is not None:
        line = _w(sp, "line")
        item["spacing"] = {"before": _tw(_w(sp, "before")), "after": _tw(_w(sp, "after")),
                           "line": int(line) if line and line.isdigit() else None, "rule": _w(sp, "lineRule")}
    if ind is not None:
        item["indent"] = {k: _tw(_w(ind, k)) for k in ("left", "right", "firstLine", "hanging") if _w(ind, k)}
    if jc is not None:
        item["align"] = _w(jc, "val")
    breaks = [_w(b, "type") or "line" for b in p.iter(f"{{{W}}}br")]
    if breaks:
        item["breaks"] = breaks
    tabs = len(list(p.iter(f"{{{W}}}tab")))
    if tabs:
        item["tabs"] = tabs
    drawings = _drawings(p)
    if drawings:
        item["drawings"] = drawings
    sect = ppr.find("w:sectPr", NS) if ppr is not None else None
    if sect is not None:
        item["section_end"] = _section(sect)
    return item


def _table(t) -> dict[str, Any]:
    tpr = t.find("w:tblPr", NS)
    rows = []
    for tr in t.findall("w:tr", NS):
        h = tr.find("w:trPr/w:trHeight", NS)
        cells = tr.findall("w:tc", NS)
        rows.append({
            "cells": len(cells),
            "height": _tw(_w(h, "val")),
            "rule": _w(h, "hRule") if h is not None else None,
            "spans": [int(_w(g, "val")) for c in cells for g in c.findall("w:tcPr/w:gridSpan", NS)] or None,
            "chars": sum(_runs(c)["chars"] for c in cells),
            "drawings": sum(len(_drawings(c)) for c in cells) or None,
        })
    return {
        "kind": "table",
        "width": _tw(_w(tpr.find("w:tblW", NS) if tpr is not None else None, "w")),
        "indent": _tw(_w(tpr.find("w:tblInd", NS) if tpr is not None else None, "w")),
        "align": _w(tpr.find("w:jc", NS) if tpr is not None else None, "val"),
        "layout": _w(tpr.find("w:tblLayout", NS) if tpr is not None else None, "type"),
        "grid": [_tw(_w(g, "w")) for g in t.findall("w:tblGrid/w:gridCol", NS)],
        "rows": rows,
        "fonts": _runs(t)["fonts"],
        "nested_tables": len(t.findall(".//w:tbl", NS)),
    }


def _docx_report(docx: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(docx)) as z:
        root = etree.fromstring(z.read("word/document.xml"))
        names = z.namelist()
    body = root.find("w:body", NS)
    items = []
    for child in body:
        tag = etree.QName(child).localname
        if tag == "p":
            items.append(_paragraph(child))
        elif tag == "tbl":
            items.append(_table(child))
        elif tag == "sectPr":
            items.append({"kind": "final_section", **_section(child)})
        else:
            items.append({"kind": tag})
    fonts = sorted({f for i in items for f in i.get("fonts", [])})
    return {
        "body_items": len(items),
        "sections": sum(1 for i in items if "section_end" in i or i["kind"] == "final_section"),
        "fonts": fonts,
        "media_files": sum(1 for n in names if n.startswith("word/media/")),
        "body": items[:MAX_BODY_ITEMS],
    }


def report(pdf: bytes, docx: Optional[bytes] = None, password: Optional[str] = None, extra: Optional[dict] = None) -> str:
    """Return the diagnostic report as JSON text. ``docx`` may be None (e.g. failed conversion)."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        pdf2docx_version = version("pdf2docx")
    except PackageNotFoundError:
        pdf2docx_version = None
    data = {
        "report": "pdf2word-local diagnostics v1 (layout only, no content)",
        "versions": {"pymupdf": pymupdf.VersionBind, "pdf2docx": pdf2docx_version, **(extra or {})},
        "pdf": _pdf_report(pdf, password),
        "docx": _docx_report(docx) if docx else None,
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
