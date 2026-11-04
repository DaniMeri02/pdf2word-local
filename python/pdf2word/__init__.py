"""Conversion engine: digital PDF -> DOCX with editable flow.

Same code for: desktop tests, the PWA's Pyodide Web Worker, the Termux script.
No network access: works only on bytes in memory.
"""

from __future__ import annotations

import io
import logging
from typing import Callable, Optional

import pymupdf
from pdf2docx import Converter

from .charts import rasterize_charts
from .docx_fixes import fix_docx

__all__ = ["convert", "PasswordRequired"]

# progress(done, total, phase) — phase: "parse" | "write"
Progress = Callable[[int, int, str], None]


class PasswordRequired(Exception):
    """The PDF is protected and the password is missing or wrong."""


class _PageProgress(logging.Handler):
    """Captures pdf2docx's '(i/n) Page p' log records to report progress."""

    def __init__(self, progress: Progress):
        super().__init__(level=logging.INFO)
        self.progress = progress
        self.phase = "parse"

    def emit(self, record: logging.LogRecord) -> None:
        msg = str(record.msg)
        if "[4/4]" in msg:
            self.phase = "write"
        elif msg == "(%d/%d) Page %d" and record.args:
            i, n, _ = record.args
            self.progress(i, n, self.phase)


def convert(pdf: bytes, password: Optional[str] = None, progress: Optional[Progress] = None) -> bytes:
    """Convert the bytes of a digital PDF into the bytes of a DOCX."""
    # Portability fixes for viewers other than Word desktop (see docx_fixes.py).
    return fix_docx(convert_unfixed(pdf, password, progress))


def convert_unfixed(pdf: bytes, password: Optional[str] = None, progress: Optional[Progress] = None) -> bytes:
    """Chart pre-processing + pdf2docx, without the DOCX fixes (used by tests)."""
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise PasswordRequired()
    # Bar charts & similar -> images, otherwise they become empty tables.
    if rasterize_charts(doc):
        pdf = doc.tobytes(garbage=3, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
        password = None  # saved without encryption: password no longer needed
    doc.close()

    logger = logging.getLogger()
    handler = None
    level = logger.level
    if progress:
        handler = _PageProgress(progress)
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
            logger.setLevel(level)
    return out.getvalue()
