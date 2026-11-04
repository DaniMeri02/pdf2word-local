// Interfaccia: registra il service worker (cache offline + CSP), avvia il Web Worker
// con il motore e gestisce scelta del file, avanzamento, password e download.
// Il PDF passa solo tra questa pagina e il worker: nessuna richiesta di rete.

"use strict";

const $ = (id) => document.getElementById(id);
const el = {
  spia: $("spia-motore"),
  testoMotore: $("testo-motore"),
  notaMotore: $("nota-motore"),
  scegli: $("scegli"),
  file: $("file"),
  nomeFile: $("nome-file"),
  formPassword: $("form-password"),
  etichettaPassword: $("etichetta-password"),
  password: $("password"),
  avanzamento: $("avanzamento"),
  barra: $("barra"),
  testoAvanzamento: $("testo-avanzamento"),
  esito: $("esito"),
  testoEsito: $("testo-esito"),
  scarica: $("scarica"),
  condividi: $("condividi"),
  errore: $("errore"),
};

const MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
let worker = null;
let motorePronto = false;
let corrente = null; // {id, nome, pdf: ArrayBuffer, inizio}
let urlDocx = null;
let fileDocx = null;
let inAttesa = null; // file arrivato prima che il motore fosse pronto

function mostra(elemento, visibile) {
  elemento.hidden = !visibile;
}

function statoMotore(testo, stato = "carica") {
  el.testoMotore.textContent = testo;
  el.spia.dataset.stato = stato;
}

function errore(msg) {
  el.errore.textContent = msg;
  mostra(el.errore, Boolean(msg));
}

function abilitaScelta(si) {
  el.file.disabled = !si;
  el.scegli.setAttribute("aria-disabled", String(!si));
}

// --- Service worker ---------------------------------------------------------

async function attendiServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    throw new Error("Questo browser non supporta i service worker: usa Chrome aggiornato.");
  }
  const sw = navigator.serviceWorker;
  const controllato = new Promise((ok) => sw.addEventListener("controllerchange", ok, { once: true }));
  await sw.register("sw.js");
  if (sw.controller) return;
  // Primo avvio: il service worker scarica e mette in cache l'intera app.
  mostra(el.notaMotore, true);
  statoMotore("Download dell'app per l'uso offline…");
  await sw.ready;
  await Promise.race([controllato, new Promise((ok) => setTimeout(ok, 3000))]);
  if (sw.controller) return;
  // Service worker attivo ma pagina non controllata (es. ricarica forzata):
  // senza di lui il worker non riceverebbe la CSP, quindi ricarico una volta.
  let giàRicaricata = false;
  try {
    giàRicaricata = sessionStorage.getItem("ricarica-sw") === "1";
    sessionStorage.setItem("ricarica-sw", "1");
  } catch {
    /* storage non disponibile */
  }
  if (giàRicaricata) throw new Error("Service worker non attivo: ricarica la pagina normalmente.");
  location.reload();
  await new Promise(() => {});
}

// --- Worker -------------------------------------------------------------------

function avviaWorker() {
  worker = new Worker("worker.js");
  worker.onmessage = ({ data: m }) => {
    switch (m.tipo) {
      case "stato":
        statoMotore(m.testo);
        break;
      case "pronto":
        motorePronto = true;
        mostra(el.notaMotore, false);
        statoMotore("Pronto, anche offline", "pronto");
        abilitaScelta(true);
        if (inAttesa) {
          const f = inAttesa;
          inAttesa = null;
          converti(f.nome, f.pdf);
        }
        break;
      case "avanzamento":
        if (corrente?.id === m.id) avanzamento(m);
        break;
      case "risultato":
        if (corrente?.id === m.id) risultato(m.docx);
        break;
      case "password":
        if (corrente?.id === m.id) chiediPassword(m.errata);
        break;
      case "errore":
        if (m.id === undefined) statoMotore("Motore non disponibile", "errore");
        if (m.id === undefined || corrente?.id === m.id) fine(`Errore: ${m.messaggio}`);
        break;
    }
  };
  worker.onerror = (e) => {
    statoMotore("Motore non disponibile", "errore");
    fine(`Errore del motore: ${e.message || "sconosciuto"}`);
  };
}

// --- Conversione ----------------------------------------------------------------

function nomeDocx(nome) {
  return (nome.replace(/\.pdf$/i, "") || "documento") + ".docx";
}

function eUnPdf(buf) {
  const t = new Uint8Array(buf, 0, Math.min(1024, buf.byteLength));
  return new TextDecoder("latin1").decode(t).includes("%PDF-");
}

function converti(nome, pdf, password) {
  errore("");
  mostra(el.esito, false);
  mostra(el.formPassword, false);
  el.nomeFile.textContent = nome;
  mostra(el.nomeFile, true);
  if (!eUnPdf(pdf)) {
    errore("Il file scelto non sembra un PDF.");
    return;
  }
  if (!motorePronto) {
    inAttesa = { nome, pdf };
    el.nomeFile.textContent = `${nome} — in attesa che il motore sia pronto…`;
    return;
  }
  corrente = { id: (corrente?.id ?? 0) + 1, nome, pdf, inizio: performance.now() };
  abilitaScelta(false);
  el.barra.value = 0;
  el.testoAvanzamento.textContent = "Apertura del documento…";
  mostra(el.avanzamento, true);
  // Copia: il buffer originale serve se bisogna riprovare con la password.
  const copia = pdf.slice(0);
  worker.postMessage({ tipo: "converti", id: corrente.id, pdf: copia, password }, [copia]);
}

function avanzamento({ fatto, totale, fase }) {
  // Analisi = 80% del lavoro, scrittura del DOCX = 20%.
  const quota = fase === "analisi" ? (fatto / totale) * 80 : 80 + (fatto / totale) * 20;
  el.barra.value = Math.round(quota);
  el.testoAvanzamento.textContent =
    fase === "analisi" ? `Analisi pagina ${fatto} di ${totale}` : `Scrittura pagina ${fatto} di ${totale}`;
}

function risultato(docx) {
  const secondi = ((performance.now() - corrente.inizio) / 1000).toFixed(1);
  const nome = nomeDocx(corrente.nome);
  if (urlDocx) URL.revokeObjectURL(urlDocx);
  fileDocx = new File([docx], nome, { type: MIME_DOCX });
  urlDocx = URL.createObjectURL(fileDocx);
  el.scarica.href = urlDocx;
  el.scarica.download = nome;
  el.testoEsito.textContent = `Fatto in ${secondi} s: ${nome} (${(docx.byteLength / 1024).toFixed(0)} KB)`;
  mostra(el.condividi, Boolean(navigator.canShare?.({ files: [fileDocx] })));
  mostra(el.esito, true);
  fine();
}

function chiediPassword(errata) {
  el.etichettaPassword.textContent = errata
    ? "Password errata, riprova"
    : "Il PDF è protetto: inserisci la password";
  mostra(el.avanzamento, false);
  mostra(el.formPassword, true);
  el.password.value = "";
  el.password.focus();
}

function fine(msgErrore) {
  mostra(el.avanzamento, false);
  if (msgErrore) errore(msgErrore);
  abilitaScelta(motorePronto);
  el.file.value = "";
}

// --- PDF condiviso da un'altra app (Web Share Target) ----------------------------

async function leggiCondiviso() {
  const parametri = new URLSearchParams(location.search);
  if (!parametri.has("condiviso")) return;
  history.replaceState(null, "", location.pathname);
  const cache = await caches.open("pdf2word-condivisi");
  const chiave = new URL("condiviso.pdf", document.baseURI).href;
  const r = await cache.match(chiave);
  if (!r) return;
  await cache.delete(chiave); // nessuna copia resta nel browser
  const nome = decodeURIComponent(r.headers.get("X-Nome-File") || "documento.pdf");
  converti(nome, await r.arrayBuffer());
}

// --- Eventi ---------------------------------------------------------------------

el.file.addEventListener("change", async () => {
  const f = el.file.files?.[0];
  if (f) converti(f.name, await f.arrayBuffer());
});

el.formPassword.addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (corrente) converti(corrente.nome, corrente.pdf, el.password.value);
});

el.condividi.addEventListener("click", () => {
  navigator.share({ files: [fileDocx], title: fileDocx.name }).catch(() => {});
});

(async () => {
  try {
    await attendiServiceWorker();
    try {
      sessionStorage.removeItem("ricarica-sw");
    } catch {
      /* storage non disponibile */
    }
    statoMotore("Avvio del motore…");
    avviaWorker();
    await leggiCondiviso();
  } catch (e) {
    statoMotore("Avvio non riuscito", "errore");
    errore(e.message || String(e));
  }
})();
