# pdf2word-local

PDF to editable Word (DOCX) converter that runs **entirely on your device**. The PDF is never uploaded to a server: conversion happens in the browser, even in airplane mode.

**App:** https://danimeri02.github.io/pdf2word-local/ (interface in English or Italian, following the device language)

## How it works

- **Engine**: [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) rebuilds paragraphs, tables, images and columns into a DOCX with editable flow. It relies on [PyMuPDF](https://github.com/pymupdf/PyMuPDF).
- **Pre-processing** (`python/pdf2word/`): charts made only of rectangles and lines are turned into images; otherwise pdf2docx would mistake them for empty tables.
- **In the browser**: Python runs with [Pyodide](https://pyodide.org/) in a Web Worker, with PyMuPDF from the Pyodide distribution. Everything (about 45 MB) is served from the same site and cached by the service worker: after the first run it also works offline.
- **Fallback**: the same engine runs on Android with Termux (`termux/install.sh`).

It works with **digital PDFs** (selectable text). Scanned PDFs (OCR) are not supported.

## Privacy

- No uploads: the file stays in the browser's memory.
- No analytics and no external resources at runtime. A Content-Security-Policy (`connect-src 'self'`) on both page and worker blocks any connection to other sites.
- The code is public and auditable.

## Using the app

Open the site in Chrome on Android, then menu ⋮ → **Install app**. Then:

- **Choose PDF** inside the app, or
- from another app (Files, Gmail, …): **Share → PDF to Word**.

The DOCX is saved to Downloads, or **Open with…** sends it straight to Word.

## Known issues

- **Word for Android** opens documents in *mobile view*, which reflows and enlarges the text. Switch to **Print Layout** to see the real page.
- Some mobile viewers (e.g. the "Documents" app on Realme phones) were seen showing a one-page document on two pages, while Word showed it on one. Prefer Word to open the DOCX.

## Layout

| Path | Content |
|---|---|
| `python/pdf2word/` | Shared conversion engine (PWA, Termux, tests) |
| `spike/` | Desktop quality tests: generate synthetic PDFs and convert them |
| `web/` | PWA: UI, translations, Web Worker, service worker, manifest |
| `scripts/prepare_vendor.py` | Download and verify (sha256) Pyodide and packages into `web/vendor/` |
| `tests/e2e_pwa.mjs` | End-to-end test in headless Chrome, run before every deploy |
| `termux/` | Command-line fallback for Termux |
| `.github/workflows/pages.yml` | Prepare, test and publish to GitHub Pages |
| `docs/adr/` | Architecture decisions |
| `GLOSSARY.md` | Domain glossary |

## Desktop tests

```sh
cd spike
python3 -m venv .venv
.venv/bin/pip install pdf2docx reportlab
.venv/bin/python make_test_pdfs.py pdf
.venv/bin/python convert_all.py pdf docx
```

PWA locally with the end-to-end test (needs Chrome):

```sh
python3 scripts/prepare_vendor.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory web &
(cd tests && npm install)
node tests/e2e_pwa.mjs http://127.0.0.1:8080/ spike/pdf /tmp/e2e-docx
```

## License

[AGPL-3.0](LICENSE). PyMuPDF and MuPDF are distributed by Artifex under AGPL-3.0; pdf2docx is MIT.
