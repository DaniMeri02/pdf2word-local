# pdf2word-locale

Convertitore da PDF a Word (DOCX) modificabile che funziona **interamente sul tuo dispositivo**. Il PDF non viene mai caricato su un server: la conversione avviene nel browser, anche in modalità aereo.

> Stato: PWA pronta e testata in Chrome (conversione, password, condivisione da altre app, offline). Ripiego Termux incluso.

## Come funziona

- **Motore**: [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) ricostruisce paragrafi, tabelle, immagini e colonne in un DOCX in flusso editabile. Si appoggia su [PyMuPDF](https://github.com/pymupdf/PyMuPDF).
- **Pre-elaborazione** (`python/pdf2word/`): i grafici fatti solo di rettangoli e linee vengono convertiti in immagini, altrimenti pdf2docx li scambierebbe per tabelle vuote.
- **Nel browser**: Python gira con [Pyodide](https://pyodide.org/) in un Web Worker, con PyMuPDF dalla distribuzione Pyodide. Tutto (circa 45 MB) è servito dallo stesso sito e messo in cache dal service worker: dopo il primo avvio funziona anche offline.
- **Ripiego**: lo stesso motore gira su Android con Termux (`termux/install.sh`).

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
| `web/` | PWA: interfaccia, Web Worker, service worker, manifest |
| `scripts/prepara_vendor.py` | Scarica e verifica (sha256) Pyodide e pacchetti in `web/vendor/` |
| `tests/e2e_pwa.mjs` | Test end-to-end in Chrome headless, eseguito prima di ogni deploy |
| `termux/` | Ripiego da riga di comando per Termux |
| `.github/workflows/pages.yml` | Prepara, testa e pubblica su GitHub Pages |
| `docs/adr/` | Decisioni architetturali |
| `GLOSSARY.md` | Glossario del dominio |

## Usare l'app

Apri il sito da Chrome su Android, poi menu ⋮ → **Installa app**. Dopo:

- **Scegli PDF** dall'app, oppure
- da un'altra app (File, Gmail, …): **Condividi → PDF in Word**.

Il DOCX si scarica in Download, oppure con **Apri con…** va direttamente a Word.

## Test sul computer

```sh
cd spike
python3 -m venv .venv
.venv/bin/pip install pdf2docx reportlab
.venv/bin/python genera_pdf.py pdf
.venv/bin/python converti.py pdf docx
```

PWA in locale con test end-to-end (serve Chrome):

```sh
python3 scripts/prepara_vendor.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory web &
(cd tests && npm install)
node tests/e2e_pwa.mjs http://127.0.0.1:8080/ spike/pdf /tmp/e2e-docx
```

## Licenza

[AGPL-3.0](LICENSE). PyMuPDF e MuPDF sono distribuiti da Artifex sotto AGPL-3.0; pdf2docx è MIT.
