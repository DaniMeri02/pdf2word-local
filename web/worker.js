// Web Worker: esegue Pyodide e il motore pdf2word fuori dal thread dell'interfaccia.
// Carica tutto da vendor/ (stesso sito); il service worker lo serve dalla cache
// con una CSP che vieta connessioni verso altri siti.
//
// Messaggi in ingresso:  {tipo: "converti", id, pdf: ArrayBuffer, password?}
// Messaggi in uscita:    {tipo: "stato", testo} | {tipo: "pronto"} |
//                        {tipo: "avanzamento", id, fatto, totale, fase} |
//                        {tipo: "risultato", id, docx: ArrayBuffer} |
//                        {tipo: "password", id, errata} | {tipo: "errore", id?, messaggio}

/* global importScripts, loadPyodide */
importScripts("vendor/pyodide/pyodide.js");

const stato = (testo) => postMessage({ tipo: "stato", testo });

async function avvia() {
  const manifest = await (await fetch("vendor/manifest.json")).json();
  stato("Avvio di Python…");
  const py = await loadPyodide({ indexURL: new URL("vendor/pyodide/", self.location).href });

  stato("Caricamento delle librerie…");
  await py.loadPackage(manifest.pacchetti, { messageCallback: () => {} });
  await py.loadPackage(manifest.wheels.map((w) => new URL(w, self.location).href), { messageCallback: () => {} });

  stato("Caricamento del motore di conversione…");
  py.FS.mkdirTree("/motore/pdf2word");
  for (const f of manifest.motore) {
    const testo = await (await fetch(f)).text();
    py.FS.writeFile("/motore/pdf2word/" + f.split("/").pop(), testo);
  }
  py.runPython(`
import sys, logging
sys.path.insert(0, "/motore")
logging.getLogger().setLevel(logging.WARNING)
import pdf2word
`);
  return py;
}

const pronto = avvia().then(
  (py) => {
    postMessage({ tipo: "pronto" });
    return py;
  },
  (e) => {
    postMessage({ tipo: "errore", messaggio: "Impossibile avviare il motore: " + (e?.message ?? e) });
    throw e;
  },
);

async function converti({ id, pdf, password }) {
  const py = await pronto;
  const FS = py.FS;
  FS.writeFile("/in.pdf", new Uint8Array(pdf));
  py.globals.set("avanzamento_js", (fatto, totale, fase) =>
    postMessage({ tipo: "avanzamento", id, fatto, totale, fase }),
  );
  py.globals.set("password_js", password ?? null);
  try {
    const esito = py.runPython(`
import pdf2word
with open("/in.pdf", "rb") as f:
    _dati = f.read()
try:
    _out = pdf2word.converti(_dati, password=password_js, progress=lambda i, n, fase: avanzamento_js(i, n, fase))
    with open("/out.docx", "wb") as f:
        f.write(_out)
    _esito = "ok"
except pdf2word.PasswordRichiesta:
    _esito = "password"
finally:
    del _dati
_esito
`);
    if (esito === "password") {
      postMessage({ tipo: "password", id, errata: Boolean(password) });
      return;
    }
    const docx = FS.readFile("/out.docx");
    postMessage({ tipo: "risultato", id, docx: docx.buffer }, [docx.buffer]);
  } catch (e) {
    const msg = String(e?.message ?? e);
    // Dal traceback Python tieni solo l'ultima riga, quella con l'errore.
    const righe = msg.trim().split("\n");
    postMessage({ tipo: "errore", id, messaggio: righe[righe.length - 1] });
  } finally {
    // Nessuna copia del documento resta nel filesystem virtuale.
    for (const f of ["/in.pdf", "/out.docx"]) {
      try {
        FS.unlink(f);
      } catch {
        /* già assente */
      }
    }
    py.runPython("globals().pop('_out', None); globals().pop('password_js', None)");
  }
}

onmessage = (ev) => {
  if (ev.data?.tipo === "converti") {
    converti(ev.data).catch((e) => postMessage({ tipo: "errore", id: ev.data.id, messaggio: String(e?.message ?? e) }));
  }
};
