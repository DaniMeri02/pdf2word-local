---
status: accepted, partly superseded by ADR-0002 (PyMuPDF from the Pyodide distribution)
---

# pdf2docx inside Pyodide, with a PyMuPDF wasm wheel we build ourselves

The PDF must never leave the phone, and we need a DOCX with editable flow (tables, columns, images). So the conversion engine is pdf2docx (Python), run in the browser with Pyodide. PyMuPDF is not shipped for Pyodide and cannot be installed with micropip (shared libraries): we build it ourselves in GitHub Actions (official procedure via cibuildwheel) and publish it as a release. The Pyodide version is pinned in `web/pyodide-version.txt`; the wheel must be rebuilt whenever it changes.

## Considered options

- **pdf.js + JS `docx` library**: extracts text only. Loses tables, columns and images, and no mature project exists.
- **LibreOffice (Termux/proot)**: imports the PDF as a drawing, with positioned boxes. That is a positioned layout, not an editable flow.
- **Native Android app (pdfbox-android + Apache POI)**: the layout reconstruction would have to be rewritten from scratch.
- **Termux with pdf2docx**: same quality and easier to install reliably, but command line only. Kept as a fallback, using the same `python/pdf2word` module.

## Consequences

- The PWA's first load downloads about 30 MB (Pyodide runtime and packages) plus the PyMuPDF wheel. After that it works offline from the cache.
- PyMuPDF/MuPDF are AGPL-3.0, so the repo is public and licensed AGPL-3.0.
- pdf2docx is no longer actively maintained by Artifex. Defects are fixed in our pre-processing (see `python/pdf2word/charts.py`), not in the package.
