#!/data/data/com.termux/files/usr/bin/bash
# Installa il convertitore in Termux (Android). Ripiego della PWA: stesso motore.
#
#   pkg install git
#   git clone https://github.com/DaniMeri02/pdf2word-locale
#   bash pdf2word-locale/termux/install.sh
#
# PyMuPDF e OpenCV vengono dai pacchetti Termux: `pip install pymupdf` su Android fallisce.
set -euo pipefail

QUI="$(cd "$(dirname "$0")" && pwd)"

pkg update -y
pkg install -y x11-repo                     # contiene python-opencv-python
pkg install -y python python-pymupdf python-opencv-python python-numpy python-lxml

# pdf2docx senza dipendenze: altrimenti pip prova a compilare opencv-python-headless e PyMuPDF.
pip install --no-deps pdf2docx==0.5.13
pip install python-docx==1.2.0 fonttools

# Accesso alla cartella Download per salvare i DOCX.
[ -d "$HOME/storage" ] || termux-setup-storage

mkdir -p "$HOME/bin"
chmod +x "$QUI/termux-file-editor"
ln -sf "$QUI/termux-file-editor" "$HOME/bin/termux-file-editor"

python -c "import pymupdf, pdf2docx, docx; print('Motore pronto: PyMuPDF', pymupdf.VersionBind)"
echo
echo "Uso:"
echo "  - da un'app: Condividi -> Termux -> Edit  (il DOCX finisce in Download)"
echo "  - da terminale: python $QUI/converti.py documento.pdf"
