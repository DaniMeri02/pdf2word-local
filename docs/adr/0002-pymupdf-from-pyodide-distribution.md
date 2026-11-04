# PyMuPDF from the Pyodide distribution, not built by us

Supersedes the "PyMuPDF wheel built by us" part of [ADR 0001](0001-pdf2docx-in-pyodide.md).

Pyodide 0.28.3 already ships PyMuPDF 1.26.3, built and tested by the Pyodide project. We use it and dropped the build workflow. pdf2docx 0.5.13 declares PyMuPDF>=1.26.7, but with 1.26.3 it produces DOCX identical to 2.1's. The comparison covered the `spike/` PDFs (text, tables, images, sections, formatting) and also holds for password-protected PDFs. That is why pdf2docx is installed without dependencies.

## Consequences

- No experimental build to maintain. Updating PyMuPDF means updating `web/pyodide-version.txt`.
- On every Pyodide version change the comparison must be redone: `spike/convert_all.py` with native PyMuPDF at the same version, against the end-to-end test output.
- The custom build (PyMuPDF 2.1 / MuPDF 1.28) worked once and is in git history (`.github/workflows/build-pymupdf-wasm.yml`, commit `ff51803`). It is the fallback if we ever need a newer PyMuPDF than Pyodide's.
