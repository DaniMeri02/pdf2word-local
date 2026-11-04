"""Motore di conversione PDF digitale -> DOCX in flusso editabile.

Stesso codice per: test sul Mac, Web Worker Pyodide della PWA, script Termux.
Nessun accesso alla rete: lavora solo su byte in memoria.
"""

from __future__ import annotations

import io
import logging
from typing import Callable, Optional

import pymupdf
from pdf2docx import Converter

from .grafici import rasterizza_grafici

__all__ = ["converti", "PasswordRichiesta"]

# progress(fatto, totale, fase) — fase: "analisi" | "scrittura"
Progresso = Callable[[int, int, str], None]


class PasswordRichiesta(Exception):
    """Il PDF è protetto e la password manca o è errata."""


class _AvanzamentoPagine(logging.Handler):
    """Intercetta i log di pdf2docx '(i/n) Page p' per riportare l'avanzamento."""

    def __init__(self, progress: Progresso):
        super().__init__(level=logging.INFO)
        self.progress = progress
        self.fase = "analisi"

    def emit(self, record: logging.LogRecord) -> None:
        msg = str(record.msg)
        if "[4/4]" in msg:
            self.fase = "scrittura"
        elif msg == "(%d/%d) Page %d" and record.args:
            i, n, _ = record.args
            self.progress(i, n, self.fase)


def converti(pdf: bytes, password: Optional[str] = None, progress: Optional[Progresso] = None) -> bytes:
    """Converte i byte di un PDF digitale nei byte di un DOCX."""
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise PasswordRichiesta()
    # Grafici a barre & simili -> immagini, altrimenti diventano tabelle vuote.
    if rasterizza_grafici(doc):
        pdf = doc.tobytes(garbage=3, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
        password = None  # salvato senza cifratura: password non più necessaria
    doc.close()

    logger = logging.getLogger()
    handler = None
    livello = logger.level
    if progress:
        handler = _AvanzamentoPagine(progress)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    try:
        cv = Converter(stream=pdf, password=password)
        try:
            out = io.BytesIO()
            cv.convert(out)
        finally:
            cv.close()
    finally:
        if handler:
            logger.removeHandler(handler)
            logger.setLevel(livello)
    return out.getvalue()
