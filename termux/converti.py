"""Converte un PDF digitale in DOCX con il motore pdf2word (stesso codice della PWA).

Uso:
  python converti.py documento.pdf [uscita.docx] [--password PWD]

Senza uscita, il DOCX va accanto al PDF con lo stesso nome.
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

from pdf2word import PasswordRichiesta, converti  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF digitale -> DOCX, tutto in locale.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("docx", type=Path, nargs="?")
    ap.add_argument("--password")
    a = ap.parse_args()
    logging.getLogger().setLevel(logging.WARNING)

    uscita = a.docx or a.pdf.with_suffix(".docx")
    dati = a.pdf.read_bytes()

    def avanzamento(i: int, n: int, fase: str) -> None:
        print(f"\r{fase} {i}/{n}   ", end="", file=sys.stderr, flush=True)

    password = a.password
    for _ in range(3):
        try:
            docx = converti(dati, password=password, progress=avanzamento)
            break
        except PasswordRichiesta:
            if not sys.stdin.isatty():
                print("PDF protetto: usa --password", file=sys.stderr)
                return 2
            password = getpass.getpass("\nPDF protetto, password: ")
    else:
        print("Password errata.", file=sys.stderr)
        return 2

    uscita.write_bytes(docx)
    print(f"\n{uscita}", file=sys.stderr)
    print(uscita)
    return 0


if __name__ == "__main__":
    sys.exit(main())
