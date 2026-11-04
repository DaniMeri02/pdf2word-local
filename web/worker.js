// Web Worker: runs Pyodide and the pdf2word engine off the UI thread.
// Everything is loaded from vendor/ (same site); the service worker serves it from
// the cache with a CSP that forbids connections to other sites.
//
// Incoming messages:  {type: "convert", id, pdf: ArrayBuffer, password?} |
//                     {type: "diagnose", id, pdf: ArrayBuffer, docx?: ArrayBuffer, password?}
// Outgoing messages:  {type: "status", key} | {type: "ready"} |
//                     {type: "progress", id, done, total, phase} |
//                     {type: "result", id, docx: ArrayBuffer} |
//                     {type: "password", id, wrong} | {type: "error", id?, message} |
//                     {type: "diagnostics", id, text?, error?}

/* global importScripts, loadPyodide */
importScripts("vendor/pyodide/pyodide.js");

const status = (key) => postMessage({ type: "status", key });
let manifestVersion = null;

async function start() {
  const manifest = await (await fetch("vendor/manifest.json")).json();
  manifestVersion = `pyodide ${manifest.pyodide}`;
  status("engine.startingPython");
  const py = await loadPyodide({ indexURL: new URL("vendor/pyodide/", self.location).href });

  status("engine.loadingLibraries");
  await py.loadPackage(manifest.packages, { messageCallback: () => {} });
  await py.loadPackage(manifest.wheels.map((w) => new URL(w, self.location).href), { messageCallback: () => {} });

  status("engine.loadingEngine");
  py.FS.mkdirTree("/engine/pdf2word");
  for (const f of manifest.engine) {
    const source = await (await fetch(f)).text();
    py.FS.writeFile("/engine/pdf2word/" + f.split("/").pop(), source);
  }
  py.runPython(`
import sys, logging
sys.path.insert(0, "/engine")
logging.getLogger().setLevel(logging.WARNING)
import pdf2word
`);
  return py;
}

const ready = start().then(
  (py) => {
    postMessage({ type: "ready" });
    return py;
  },
  (e) => {
    postMessage({ type: "error", message: String(e?.message ?? e), startup: true });
    throw e;
  },
);

async function convert({ id, pdf, password }) {
  const py = await ready;
  const FS = py.FS;
  FS.writeFile("/in.pdf", new Uint8Array(pdf));
  py.globals.set("progress_js", (done, total, phase) => postMessage({ type: "progress", id, done, total, phase }));
  py.globals.set("password_js", password ?? null);
  try {
    const outcome = py.runPython(`
import pdf2word
with open("/in.pdf", "rb") as f:
    _data = f.read()
try:
    _out = pdf2word.convert(_data, password=password_js, progress=lambda i, n, phase: progress_js(i, n, phase))
    with open("/out.docx", "wb") as f:
        f.write(_out)
    _outcome = "ok"
except pdf2word.PasswordRequired:
    _outcome = "password"
finally:
    del _data
_outcome
`);
    if (outcome === "password") {
      postMessage({ type: "password", id, wrong: Boolean(password) });
      return;
    }
    const docx = FS.readFile("/out.docx");
    postMessage({ type: "result", id, docx: docx.buffer }, [docx.buffer]);
  } catch (e) {
    const msg = String(e?.message ?? e);
    // From a Python traceback keep only the last line, the one with the error.
    const lines = msg.trim().split("\n");
    postMessage({ type: "error", id, message: lines[lines.length - 1] });
  } finally {
    // No copy of the document stays in the virtual filesystem.
    for (const f of ["/in.pdf", "/out.docx"]) {
      try {
        FS.unlink(f);
      } catch {
        /* already gone */
      }
    }
    py.runPython("globals().pop('_out', None); globals().pop('password_js', None)");
  }
}

// Layout-only report (no text, no images) to help reproduce conversion bugs.
async function diagnose({ id, pdf, docx, password }) {
  const py = await ready;
  const FS = py.FS;
  FS.writeFile("/diag.pdf", new Uint8Array(pdf));
  if (docx) FS.writeFile("/diag.docx", new Uint8Array(docx));
  py.globals.set("password_js", password ?? null);
  py.globals.set("has_docx_js", Boolean(docx));
  py.globals.set("app_version_js", manifestVersion);
  try {
    const text = py.runPython(`
from pdf2word.diagnostics import report
with open("/diag.pdf", "rb") as f:
    _pdf = f.read()
_docx = None
if has_docx_js:
    with open("/diag.docx", "rb") as f:
        _docx = f.read()
try:
    _report = report(_pdf, _docx, password=password_js, extra={"app": app_version_js})
finally:
    del _pdf, _docx
_report
`);
    postMessage({ type: "diagnostics", id, text });
  } catch (e) {
    const lines = String(e?.message ?? e).trim().split("\n");
    postMessage({ type: "diagnostics", id, error: lines[lines.length - 1] });
  } finally {
    for (const f of ["/diag.pdf", "/diag.docx"]) {
      try {
        FS.unlink(f);
      } catch {
        /* already gone */
      }
    }
    py.runPython("globals().pop('_report', None); globals().pop('password_js', None)");
  }
}

onmessage = (ev) => {
  const m = ev.data;
  if (m?.type === "convert") {
    convert(m).catch((e) => postMessage({ type: "error", id: m.id, message: String(e?.message ?? e) }));
  } else if (m?.type === "diagnose") {
    diagnose(m).catch((e) => postMessage({ type: "diagnostics", id: m.id, error: String(e?.message ?? e) }));
  }
};
