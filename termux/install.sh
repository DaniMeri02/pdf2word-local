#!/data/data/com.termux/files/usr/bin/bash
# Install the converter in Termux (Android). Fallback for the PWA: same engine.
#
#   pkg install git
#   git clone https://github.com/DaniMeri02/pdf2word-local
#   bash pdf2word-local/termux/install.sh
#
# PyMuPDF and OpenCV come from Termux packages: `pip install pymupdf` fails on Android.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

pkg update -y
pkg install -y x11-repo                     # provides python-opencv-python
pkg install -y python python-pymupdf python-opencv-python python-numpy python-lxml

# pdf2docx without dependencies: otherwise pip tries to build opencv-python-headless and PyMuPDF.
pip install --no-deps pdf2docx==0.5.13
pip install python-docx==1.2.0 fonttools

# Access to the Download folder to save DOCX files.
[ -d "$HOME/storage" ] || termux-setup-storage

mkdir -p "$HOME/bin"
chmod +x "$HERE/termux-file-editor"
ln -sf "$HERE/termux-file-editor" "$HOME/bin/termux-file-editor"

python -c "import pymupdf, pdf2docx, docx; print('Engine ready: PyMuPDF', pymupdf.VersionBind)"
echo
echo "Usage:"
echo "  - from an app: Share -> Termux -> Edit  (the DOCX ends up in Download)"
echo "  - from the terminal: python $HERE/convert.py document.pdf"
