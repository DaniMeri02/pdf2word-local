// Web Worker: runs Pyodide and the pdf2word engine off the UI thread.
// Everything is loaded from vendor/ (same site); the service worker serves it from
// the cache with a CSP that forbids connections to other sites.
//
// Incoming messages:  {type: "convert", id, pdf: ArrayBuffer, password?}
// Outgoing messages:  {type: "status", key} | {type: "ready"} |
//                     {type: "progress", id, done, total, phase} |
//                     {type: "result", id, docx: ArrayBuffer} |
//                     {type: "password", id, wrong} | {type: "error", id?, message}

/* global importScripts, loadPyodide */
importScripts("vendor/pyodide/pyodide.js");

const status = (key) => postMessage({ type: "status", key });

async function start() {
  const manifest = await (await fetch("vendor/manifest.json")).json();
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

onmessage = (ev) => {
  if (ev.data?.type === "convert") {
    convert(ev.data).catch((e) => postMessage({ type: "error", id: ev.data.id, message: String(e?.message ?? e) }));
  }
};
