"""Convert a digital PDF to DOCX with the pdf2word engine (same code as the PWA).

Usage:
  python convert.py document.pdf [output.docx] [--password PWD]

Without an output path, the DOCX is written next to the PDF with the same name.
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

from pdf2word import PasswordRequired, convert  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Digital PDF -> DOCX, entirely on this device.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("docx", type=Path, nargs="?")
    ap.add_argument("--password")
    a = ap.parse_args()
    logging.getLogger().setLevel(logging.WARNING)

    output = a.docx or a.pdf.with_suffix(".docx")
    data = a.pdf.read_bytes()

    def progress(i: int, n: int, phase: str) -> None:
        print(f"\r{phase} {i}/{n}   ", end="", file=sys.stderr, flush=True)

    password = a.password
    for _ in range(3):
        try:
            docx = convert(data, password=password, progress=progress)
            break
        except PasswordRequired:
            if not sys.stdin.isatty():
                print("Protected PDF: use --password", file=sys.stderr)
                return 2
            password = getpass.getpass("\nProtected PDF, password: ")
    else:
        print("Wrong password.", file=sys.stderr)
        return 2

    output.write_bytes(docx)
    print(f"\n{output}", file=sys.stderr)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
