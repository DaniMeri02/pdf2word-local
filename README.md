# pdf2word-locale

Convertitore da PDF a Word (DOCX) modificabile che funziona **interamente sul tuo dispositivo**. Il PDF non viene mai caricato su un server: la conversione avviene nel browser, anche in modalità aereo.

> Stato: in sviluppo. Il motore di conversione è pronto e la build WebAssembly di PyMuPDF è in preparazione. La web app installabile (PWA) è la fase successiva.

## Come funziona

- **Motore**: [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) ricostruisce paragrafi, tabelle, immagini e colonne in un DOCX in flusso editabile. Si appoggia su [PyMuPDF](https://github.com/pymupdf/PyMuPDF).
- **Pre-elaborazione** (`python/pdf2word/`): i grafici fatti solo di rettangoli e linee vengono convertiti in immagini, altrimenti pdf2docx li scambierebbe per tabelle vuote.
- **Nel browser**: Python gira con [Pyodide](https://pyodide.org/). PyMuPDF viene compilato per WebAssembly dal workflow `.github/workflows/build-pymupdf-wasm.yml`, che lo verifica convertendo PDF di prova dentro Pyodide.
- **Ripiego**: lo stesso motore può girare su Android con Termux.

Funziona con i **PDF digitali**, cioè con testo selezionabile. I PDF scansionati (OCR) non sono supportati.

## Privacy

- Nessun upload: il file resta in memoria nel browser.
- Nessuna analytics e nessuna risorsa esterna a runtime: tutto è servito dallo stesso sito e poi messo in cache per l'uso offline.
- Il codice è pubblico e verificabile.

## Struttura

| Percorso | Contenuto |
|---|---|
| `python/pdf2word/` | Motore di conversione condiviso (PWA, Termux, test) |
| `spike/` | Test di qualità sul computer: genera PDF sintetici e li converte |
| `tests/smoke_pyodide.mjs` | Conversione reale dentro Pyodide (Node), usata dalla CI |
| `.github/workflows/` | Build di PyMuPDF per WebAssembly |
| `docs/adr/` | Decisioni architetturali |
| `GLOSSARY.md` | Glossario del dominio |

## Test sul computer

```sh
cd spike
python3 -m venv .venv
.venv/bin/pip install pdf2docx reportlab
.venv/bin/python genera_pdf.py pdf
.venv/bin/python converti.py pdf docx
```

## Licenza

[AGPL-3.0](LICENSE). PyMuPDF e MuPDF sono distribuiti da Artifex sotto AGPL-3.0; pdf2docx è MIT.
