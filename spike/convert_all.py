"""Convert every PDF in a folder to DOCX with the pdf2word engine and time it.

Usage: .venv/bin/python convert_all.py [pdf_dir] [docx_dir]
Password-protected test PDFs (protected_*) are skipped.
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pymupdf  # noqa: E402

from pdf2word import convert  # noqa: E402
from pdf2word.charts import find_charts  # noqa: E402

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "pdf")
DST = Path(sys.argv[2] if len(sys.argv) > 2 else "docx")
DST.mkdir(parents=True, exist_ok=True)
logging.getLogger().setLevel(logging.WARNING)

for pdf in sorted(p for p in SRC.glob("*.pdf") if not p.name.startswith("protected")):
    out = DST / (pdf.stem + ".docx")
    data = pdf.read_bytes()
    with pymupdf.open(stream=data) as d:
        pages = d.page_count
        charts = sum(len(find_charts(p)) for p in d)
    t0 = time.perf_counter()
    out.write_bytes(convert(data))
    dt = time.perf_counter() - t0
    print(f"{pdf.name:22s} {pages:3d} pages  {charts} charts  {dt:6.2f}s  {dt / pages:5.2f}s/page  -> {out}")
