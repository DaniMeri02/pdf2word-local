"""Converte tutti i PDF di una cartella in DOCX con il motore pdf2word e misura i tempi.

Uso: .venv/bin/python converti.py [cartella_pdf] [cartella_docx]
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import pymupdf  # noqa: E402

from pdf2word import converti  # noqa: E402
from pdf2word.grafici import trova_grafici  # noqa: E402

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "pdf")
DST = Path(sys.argv[2] if len(sys.argv) > 2 else "docx")
DST.mkdir(parents=True, exist_ok=True)
logging.getLogger().setLevel(logging.WARNING)

for pdf in sorted(SRC.glob("*.pdf")):
    out = DST / (pdf.stem + ".docx")
    dati = pdf.read_bytes()
    with pymupdf.open(stream=dati) as d:
        pagine = d.page_count
        grafici = sum(len(trova_grafici(p)) for p in d)
    t0 = time.perf_counter()
    out.write_bytes(converti(dati))
    dt = time.perf_counter() - t0
    print(f"{pdf.name:22s} {pagine:3d} pag  {grafici} grafici  {dt:6.2f}s  {dt / pagine:5.2f}s/pag  -> {out}")
