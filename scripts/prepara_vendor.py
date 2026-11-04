"""Prepara web/vendor/: tutto ciò che la PWA carica, servito dallo stesso sito.

- runtime Pyodide e i pacchetti della distribuzione (PyMuPDF compreso, con le dipendenze)
  dal CDN di Pyodide
- wheel pure Python da PyPI (pdf2docx, python-docx)
- il motore python/pdf2word
- manifest.json (cosa caricare) e precache.js (cosa mettere in cache offline)

Ogni file scaricato è verificato con sha256 (lock di Pyodide / API JSON di PyPI).
Gira solo in fase di build: il browser dell'utente non contatta mai CDN o PyPI.

Uso: python scripts/prepara_vendor.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
WEB = RADICE / "web"
VENDOR = WEB / "vendor"

# Pacchetti della distribuzione Pyodide richiesti dal motore (le dipendenze si risolvono dal lock).
# PyMuPDF è compilato e testato dal progetto Pyodide (0.28.3 -> PyMuPDF 1.26.3).
PACCHETTI_PYODIDE = ["pymupdf", "numpy", "opencv-python", "fonttools", "lxml", "typing-extensions"]
# Wheel pure Python da PyPI, versioni fissate. Installate senza dipendenze:
# pdf2docx 0.5.13 dichiara PyMuPDF>=1.26.7, ma con 1.26.3 produce DOCX identici (vedi ADR 0002).
WHEEL_PYPI = {"pdf2docx": "0.5.13", "python-docx": "1.2.0"}
RUNTIME = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
# Guscio dell'app: precache insieme a vendor/.
GUSCIO = ["./", "index.html", "app.js", "worker.js", "stile.css", "manifest.webmanifest",
          "icone/icona-192.png", "icone/icona-512.png", "icone/icona-maschera-512.png"]


def scarica(url: str, dest: Path, sha256: str | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r:
        dati = r.read()
    if sha256 and hashlib.sha256(dati).hexdigest() != sha256:
        sys.exit(f"sha256 non corrisponde per {url}")
    dest.write_bytes(dati)
    print(f"  {len(dati) / 1048576:6.2f} MB  {dest.relative_to(WEB)}")


def risolvi(lock: dict, nomi: list[str]) -> list[str]:
    pacchetti = lock["packages"]
    visti: list[str] = []

    def visita(n: str) -> None:
        n = n.lower().replace("_", "-")
        if n in visti:
            return
        if n not in pacchetti:
            sys.exit(f"pacchetto {n!r} non presente nel lock di Pyodide")
        for d in pacchetti[n].get("depends", []):
            visita(d)
        visti.append(n)

    for n in nomi:
        visita(n)
    return visti


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    versione = (WEB / "pyodide-version.txt").read_text().strip()
    cdn = f"https://cdn.jsdelivr.net/pyodide/v{versione}/full/"
    if VENDOR.exists():
        shutil.rmtree(VENDOR)

    print(f"Pyodide {versione}: runtime")
    for f in RUNTIME:
        scarica(cdn + f, VENDOR / "pyodide" / f)
    lock = json.loads((VENDOR / "pyodide" / "pyodide-lock.json").read_text())

    nomi = risolvi(lock, PACCHETTI_PYODIDE)
    print(f"Pacchetti Pyodide: {', '.join(nomi)}")
    for n in nomi:
        p = lock["packages"][n]
        scarica(cdn + p["file_name"], VENDOR / "pyodide" / p["file_name"], p["sha256"])

    wheels = []
    print("Wheel PyPI")
    for nome, ver in WHEEL_PYPI.items():
        with urllib.request.urlopen(f"https://pypi.org/pypi/{nome}/{ver}/json") as r:
            info = json.load(r)
        whl = next(u for u in info["urls"] if u["packagetype"] == "bdist_wheel" and u["filename"].endswith("none-any.whl"))
        scarica(whl["url"], VENDOR / "wheels" / whl["filename"], whl["digests"]["sha256"])
        wheels.append(f"vendor/wheels/{whl['filename']}")

    motore = []
    (VENDOR / "pdf2word").mkdir(parents=True)
    for py in sorted((RADICE / "python" / "pdf2word").glob("*.py")):
        shutil.copy2(py, VENDOR / "pdf2word" / py.name)
        motore.append(f"vendor/pdf2word/{py.name}")

    (VENDOR / "manifest.json").write_text(json.dumps({
        "pyodide": versione,
        "pacchetti": nomi,
        "wheels": wheels,
        "motore": motore,
    }, indent=2))

    # Versione = hash di tutto ciò che va in cache: cambia -> il service worker si aggiorna.
    tutti = GUSCIO + sorted(str(p.relative_to(WEB)) for p in VENDOR.rglob("*") if p.is_file())
    h = hashlib.sha256()
    for f in tutti:
        if f != "./":
            h.update(f.encode())
            h.update((WEB / f).read_bytes())
    totale = sum((WEB / f).stat().st_size for f in tutti if f != "./")
    (VENDOR / "precache.js").write_text(
        "// Generato da scripts/prepara_vendor.py: non modificare.\n"
        f"self.PRECACHE = {json.dumps({'versione': h.hexdigest()[:12], 'byte': totale, 'file': tutti}, indent=1)};\n"
    )
    print(f"Totale da mettere in cache: {totale / 1048576:.1f} MB, versione {h.hexdigest()[:12]}")


if __name__ == "__main__":
    main()
