"""Post-processing of the DOCX written by pdf2docx, for viewers other than Word desktop.

Word for desktop is forgiving; Word for Android, Pages, LibreOffice and phone
document viewers are not. pdf2docx output has three portability problems
(found with a user's diagnostic report, see tests/test_docx_fixes.py):

1. Table grid: pdf2docx sets each cell's width (tcW) but leaves the table grid
   (tblGrid) at python-docx's default of equal columns. Viewers that trust the
   grid draw equal columns. -> Rebuild the grid from the cell widths.
2. Row heights are "exact": text that does not fit (other fonts, edits) is cut
   off. -> Use "atLeast", so rows grow instead.
3. Side-by-side blocks (e.g. logo left, address right) become multi-column
   sections separated by "nextColumn" section breaks, which some viewers turn
   into page breaks. -> Replace each such column set with a borderless table,
   one cell per column, inside a single-column section.
"""

from __future__ import annotations

import io
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def _int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# --- 1. Table grid --------------------------------------------------------------

GRID_TOLERANCE = 40  # twips (2 pt): cell edges closer than this are the same grid line


def fix_table_grid(tbl) -> bool:
    """Rebuild tblGrid from cell widths. Returns True if the grid changed."""
    grid = tbl.find(q("tblGrid"))
    if grid is None:
        return False
    cols = grid.findall(q("gridCol"))
    rows = []
    for tr in tbl.findall(q("tr")):
        cells = []
        for tc in tr.findall(q("tc")):
            w = tc.find(f"{q('tcPr')}/{q('tcW')}")
            if w is None or w.get(q("type"), "dxa") != "dxa":
                return False
            span = tc.find(f"{q('tcPr')}/{q('gridSpan')}")
            cells.append((_int(w.get(q("w"))), _int(span.get(q("val")), 1) if span is not None else 1))
        rows.append(cells)
    # Every row must cover the same number of grid columns as the grid.
    if not rows or any(sum(s for _, s in r) != len(cols) for r in rows):
        return False
    full = [r for r in rows if len(r) == len(cols)]
    if full:
        # Rows with one cell per column give the widths directly (median across rows).
        widths = [sorted(r[i][0] for r in full)[len(full) // 2] for i in range(len(cols))]
    else:
        # Otherwise: grid lines = cumulative cell edges of all rows, merged within tolerance.
        # (Cells continuing a vertical merge can carry stale widths, hence "full" rows first.)
        edges = sorted({e for r in rows for e in _cumulative(r)})
        lines = []
        for e in edges:
            if lines and e - lines[-1][-1] <= GRID_TOLERANCE:
                lines[-1].append(e)
            else:
                lines.append([e])
        positions = [round(sum(g) / len(g)) for g in lines]
        if len(positions) != len(cols) + 1:
            return False
        widths = [b - a for a, b in zip(positions, positions[1:])]
    if any(w <= 0 for w in widths):
        return False
    for col, w in zip(cols, widths):
        col.set(q("w"), str(w))
    tblpr = tbl.find(q("tblPr"))
    if tblpr is not None:
        tblw = tblpr.find(q("tblW"))
        if tblw is None:
            tblw = etree.SubElement(tblpr, q("tblW"))
        tblw.set(q("w"), str(sum(widths)))
        tblw.set(q("type"), "dxa")
    return True


def _cumulative(row):
    x, out = 0, [0]
    for w, _ in row:
        x += w
        out.append(x)
    return out


# --- 2. Row heights -------------------------------------------------------------

def fix_row_heights(root) -> int:
    n = 0
    for h in root.iter(q("trHeight")):
        if h.get(q("hRule")) == "exact":
            h.set(q("hRule"), "atLeast")
            n += 1
    return n


# --- 3. Column sections -> borderless tables ------------------------------------

def _sect_props(sect):
    cols = sect.find(q("cols"))
    kind = sect.find(q("type"))
    return {
        "type": kind.get(q("val")) if kind is not None else "nextPage",
        "num": _int(cols.get(q("num")), 1) if cols is not None else 1,
        "space": _int(cols.get(q("space")), 720) if cols is not None else 720,
        "widths": [_int(c.get(q("w"))) for c in cols.findall(q("col"))] if cols is not None else [],
        "equal": cols is None or cols.get(q("equalWidth")) != "0",
    }


def _sections(body):
    """Split the body into sections: [{content: [...], holder, sect}] in order.

    holder is the paragraph carrying the sectPr (None for the final, body-level one).
    """
    sections, content = [], []
    for child in list(body):
        if child.tag == q("sectPr"):
            sections.append({"content": content, "holder": None, "sect": child})
            content = []
            continue
        sect = child.find(f"{q('pPr')}/{q('sectPr')}") if child.tag == q("p") else None
        if sect is not None:
            sections.append({"content": content, "holder": child, "sect": sect})
            content = []
        else:
            content.append(child)
    return sections


def _text_width(sect) -> int:
    size = sect.find(q("pgSz"))
    mar = sect.find(q("pgMar"))
    page_w = _int(size.get(q("w")), 11906) if size is not None else 11906
    left = _int(mar.get(q("left")), 1440) if mar is not None else 1440
    right = _int(mar.get(q("right")), 1440) if mar is not None else 1440
    return page_w - left - right


def _holder_has_content(p) -> bool:
    return any(t.text for t in p.iter(q("t"))) or p.find(f".//{q('drawing')}") is not None


def _column_table(columns, widths, space):
    """Borderless one-row table, one cell per column, columns separated by space."""
    tbl = etree.Element(q("tbl"))
    pr = etree.SubElement(tbl, q("tblPr"))
    total = sum(widths) + space * (len(widths) - 1)
    etree.SubElement(pr, q("tblW"), {q("w"): str(total), q("type"): "dxa"})
    etree.SubElement(pr, q("tblLayout"), {q("type"): "fixed"})
    borders = etree.SubElement(pr, q("tblBorders"))
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        etree.SubElement(borders, q(side), {q("val"): "nil"})
    mar = etree.SubElement(pr, q("tblCellMar"))
    for side in ("top", "left", "bottom", "right"):
        etree.SubElement(mar, q(side), {q("w"): "0", q("type"): "dxa"})
    grid = etree.SubElement(tbl, q("tblGrid"))
    cell_widths = [w + (space if i < len(widths) - 1 else 0) for i, w in enumerate(widths)]
    for w in cell_widths:
        etree.SubElement(grid, q("gridCol"), {q("w"): str(w)})
    tr = etree.SubElement(tbl, q("tr"))
    for i, (content, w) in enumerate(zip(columns, cell_widths)):
        tc = etree.SubElement(tr, q("tc"))
        tcpr = etree.SubElement(tc, q("tcPr"))
        etree.SubElement(tcpr, q("tcW"), {q("w"): str(w), q("type"): "dxa"})
        if i < len(widths) - 1 and space:
            tcmar = etree.SubElement(tcpr, q("tcMar"))
            etree.SubElement(tcmar, q("right"), {q("w"): str(space), q("type"): "dxa"})
        for el in content:
            tc.append(el)
        # A cell must end with a paragraph.
        if not len(content) or content[-1].tag != q("p"):
            etree.SubElement(tc, q("p"))
    return tbl


def fix_column_sections(body) -> int:
    """Replace column sets (n-column section + n-1 'nextColumn' sections) with tables."""
    sections = _sections(body)
    replaced = 0
    i = 0
    while i < len(sections):
        first = _sect_props(sections[i]["sect"])
        n = first["num"]
        group = sections[i:i + n]
        if (
            n > 1
            and first["type"] != "nextColumn"
            and len(group) == n
            and all(_sect_props(s["sect"])["type"] == "nextColumn" and _sect_props(s["sect"])["num"] == n for s in group[1:])
        ):
            last = group[-1]
            # Mark where the table goes before moving the columns' content into it.
            first_el = group[0]["content"][0] if group[0]["content"] else group[0]["holder"]
            marker = etree.Element(q("p"))
            first_el.addprevious(marker)
            text_w = _text_width(last["sect"])
            if not first["equal"] and len(first["widths"]) == n:
                widths = first["widths"]
            else:
                widths = [(text_w - first["space"] * (n - 1)) // n] * n
            columns = []
            for s in group:
                col = list(s["content"])
                # Section-break paragraphs are usually empty; keep them if they carry content.
                if s is not last and s["holder"] is not None and _holder_has_content(s["holder"]):
                    s["holder"].find(q("pPr")).remove(s["sect"])
                    col.append(s["holder"])
                columns.append(col)
            table = _column_table(columns, widths, first["space"])
            marker.addprevious(table)
            body.remove(marker)
            for s in group[:-1]:
                if s["holder"] is not None and s["holder"].getparent() is body:
                    body.remove(s["holder"])
            # The last section's break stays, now as a single-column section that
            # starts the way the first column section started.
            sect = last["sect"]
            cols = sect.find(q("cols"))
            if cols is not None:
                for c in list(cols):
                    cols.remove(c)
                cols.set(q("num"), "1")
                cols.attrib.pop(q("equalWidth"), None)
            kind = sect.find(q("type"))
            if kind is None:
                kind = etree.Element(q("type"))
                sect.insert(0, kind)
            kind.set(q("val"), first["type"])
            if last["holder"] is not None and _holder_has_content(last["holder"]):
                # Keep its content in the last column, move the break to an empty paragraph.
                holder = last["holder"]
                holder.find(q("pPr")).remove(sect)
                table.findall(f"{q('tr')}/{q('tc')}")[-1].append(holder)
                p = etree.Element(q("p"))
                ppr = etree.SubElement(p, q("pPr"))
                ppr.append(sect)
                table.addnext(p)
            replaced += 1
            i += n
        else:
            i += 1
    return replaced


def fix_empty_column_sections(body) -> int:
    """Multi-column sections left with no text, image or table (e.g. a page start) -> 1 column."""
    n = 0
    for s in _sections(body):
        cols = s["sect"].find(q("cols"))
        if cols is None or _int(cols.get(q("num")), 1) <= 1:
            continue
        if any(el.tag == q("tbl") or _holder_has_content(el) for el in s["content"]):
            continue
        for c in list(cols):
            cols.remove(c)
        cols.set(q("num"), "1")
        cols.attrib.pop(q("equalWidth"), None)
        n += 1
    return n


# --- Entry point ------------------------------------------------------------------

def fix_docx(docx: bytes) -> bytes:
    """Apply all fixes to the DOCX bytes produced by pdf2docx."""
    src = zipfile.ZipFile(io.BytesIO(docx))
    root = etree.fromstring(src.read("word/document.xml"))
    body = root.find(q("body"))
    fix_column_sections(body)
    fix_empty_column_sections(body)
    for tbl in root.iter(q("tbl")):
        fix_table_grid(tbl)
    fix_row_heights(root)
    xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            dst.writestr(item, xml if item.filename == "word/document.xml" else src.read(item.filename))
    return out.getvalue()


__all__ = ["fix_docx", "fix_table_grid", "fix_row_heights", "fix_column_sections", "fix_empty_column_sections"]
