// Smoke test: converte PDF in DOCX dentro Pyodide (Node), con la wheel PyMuPDF wasm
// compilata dalla CI e il motore pdf2word. Stessa catena della PWA.
//
// Uso: node tests/smoke_pyodide.mjs <url_wheel_pymupdf> <cartella_pdf> <cartella_docx> <cartella_python>
//
// In Node i pacchetti della distribuzione Pyodide e quelli PyPI vengono scaricati
// dalla rete: va bene in CI. La PWA invece li servirà tutti da sé (offline).

import { createRequire } from "node:module";
import { mkdirSync, readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join, resolve, relative } from "node:path";

const require = createRequire(join(resolve("tests"), "package.json"));
const { loadPyodide } = require("pyodide");

const [wheelUrl, pdfDir, outDir, pyDir] = process.argv.slice(2);
if (!wheelUrl || !pdfDir || !outDir || !pyDir) {
  console.error("Uso: node tests/smoke_pyodide.mjs <url_wheel> <cartella_pdf> <cartella_docx> <cartella_python>");
  process.exit(2);
}

const t0 = performance.now();
const py = await loadPyodide();
console.log(`Pyodide ${py.version} caricato`);

await py.loadPackage(["numpy", "opencv-python", "fonttools", "lxml", "micropip", "typing-extensions"]);
await py.loadPackage(wheelUrl);
const micropip = py.pyimport("micropip");
await micropip.install.callKwargs(["pdf2docx==0.5.13", "python-docx==1.2.0"], { deps: false });

// Copia il motore pdf2word nel filesystem virtuale.
function copia(dir) {
  for (const nome of readdirSync(dir)) {
    const p = join(dir, nome);
    const dest = "/motore/" + relative(pyDir, p);
    if (statSync(p).isDirectory()) {
      if (nome === "__pycache__") continue;
      py.FS.mkdirTree(dest);
      copia(p);
    } else if (nome.endsWith(".py")) {
      py.FS.writeFile(dest, readFileSync(p));
    }
  }
}
py.FS.mkdirTree("/motore");
copia(pyDir);
py.runPython(`
import sys
sys.path.insert(0, "/motore")
import pymupdf, pdf2docx, pdf2word
print("PyMuPDF", pymupdf.VersionBind, "| MuPDF", pymupdf.VersionFitz, "| pdf2docx", pdf2docx.__name__)
`);
console.log(`Ambiente pronto in ${((performance.now() - t0) / 1000).toFixed(1)}s`);

mkdirSync(outDir, { recursive: true });
let errori = 0;
for (const nome of readdirSync(pdfDir).filter((n) => n.endsWith(".pdf")).sort()) {
  py.FS.writeFile("/in.pdf", readFileSync(join(pdfDir, nome)));
  const t = performance.now();
  try {
    const esito = py.runPython(`
import io, zipfile
from docx import Document
import pdf2word
with open("/in.pdf", "rb") as f:
    dati = f.read()
fasi = []
out = pdf2word.converti(dati, progress=lambda i, n, fase: fasi.append((fase, i, n)))
with open("/out.docx", "wb") as f:
    f.write(out)
d = Document(io.BytesIO(out))
xml = zipfile.ZipFile(io.BytesIO(out)).read("word/document.xml").decode()
assert len(out) > 0
assert fasi, "nessun avanzamento ricevuto"
f"{len(out)} byte, par={sum(1 for p in d.paragraphs if p.text.strip())} tab={len(d.tables)} img={xml.count('<pic:pic')} txbox={xml.count('<w:txbxContent')} avanzamento={len(fasi)}"
`);
    writeFileSync(join(outDir, nome.replace(/\.pdf$/, ".docx")), py.FS.readFile("/out.docx"));
    console.log(`OK  ${nome}: ${esito} in ${((performance.now() - t) / 1000).toFixed(2)}s`);
  } catch (e) {
    errori++;
    console.error(`ERR ${nome}: ${e.message ?? e}`);
  }
}
process.exit(errori ? 1 : 0);
