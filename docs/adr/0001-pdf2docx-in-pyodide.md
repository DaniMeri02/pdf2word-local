# pdf2docx dentro Pyodide, con una wheel PyMuPDF wasm compilata da noi

Il PDF non deve mai lasciare il telefono, e serve un DOCX in flusso editabile con tabelle, colonne e immagini. Per questo il motore di conversione è pdf2docx (Python), eseguito nel browser con Pyodide. PyMuPDF non è distribuito per Pyodide e non si installa con micropip, per via delle librerie condivise. Lo compiliamo noi in GitHub Actions (`.github/workflows/build-pymupdf-wasm.yml`, procedura ufficiale tramite cibuildwheel) e lo pubblichiamo come release. La versione di Pyodide è fissata in `web/pyodide-version.txt`, e la wheel va ricompilata a ogni cambio di versione.

## Opzioni considerate

- **pdf.js + libreria JS `docx`**: estrae solo testo. Perde tabelle, colonne e immagini, e non esiste un progetto maturo.
- **LibreOffice (Termux/proot)**: importa il PDF come disegno, con caselle posizionate. È un layout posizionato, non un flusso editabile.
- **App Android nativa (pdfbox-android + Apache POI)**: la ricostruzione del layout andrebbe riscritta da zero.
- **Termux con pdf2docx**: stessa qualità, più affidabile da installare, ma si usa solo da riga di comando. Resta come ripiego e usa lo stesso modulo `python/pdf2word`.

## Conseguenze

- Il primo caricamento della PWA scarica circa 30 MB (runtime e pacchetti Pyodide), più la wheel PyMuPDF. Dopo funziona offline dalla cache.
- PyMuPDF/MuPDF sono AGPL-3.0, quindi il repo è pubblico e ha licenza AGPL-3.0.
- pdf2docx non è più mantenuto attivamente da Artifex. I difetti si correggono nel nostro pre-processing (vedi `python/pdf2word/grafici.py`), non nel pacchetto.
