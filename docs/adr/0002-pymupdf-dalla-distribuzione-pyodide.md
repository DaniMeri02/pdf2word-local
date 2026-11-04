# PyMuPDF dalla distribuzione Pyodide, non compilato da noi

Sostituisce la parte "wheel PyMuPDF compilata da noi" di [ADR 0001](0001-pdf2docx-in-pyodide.md).

Pyodide 0.28.3 include già PyMuPDF 1.26.3, compilato e testato dal progetto Pyodide. Usiamo quello e abbiamo eliminato il workflow di build. pdf2docx 0.5.13 dichiara di richiedere PyMuPDF>=1.26.7, ma con la 1.26.3 produce DOCX identici a quelli della 2.1. Il confronto è stato fatto sui PDF di `spike/` (testo, tabelle, immagini, sezioni, formattazione), e regge anche con i PDF protetti da password. Per questo pdf2docx si installa senza dipendenze.

## Conseguenze

- Nessuna build sperimentale da mantenere. Aggiornare PyMuPDF significa aggiornare `web/pyodide-version.txt`.
- A ogni cambio di versione di Pyodide va rifatto il confronto: `spike/converti.py` con PyMuPDF nativo alla stessa versione, contro il risultato del test end-to-end.
- La build su misura (PyMuPDF 2.1 / MuPDF 1.28) ha funzionato una volta, ed è nella storia git (`.github/workflows/build-pymupdf-wasm.yml`, commit `ff51803`). È il ripiego se un giorno servisse una PyMuPDF più recente di quella di Pyodide.
