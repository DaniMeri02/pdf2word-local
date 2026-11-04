// Service worker:
// - mette in cache tutta l'app (Pyodide compreso) per l'uso offline;
// - serve pagina e worker con una Content-Security-Policy che vieta connessioni
//   verso altri siti (connect-src 'self'): il PDF non può uscire dal dispositivo;
// - riceve i PDF condivisi da altre app Android (Web Share Target).

/* global importScripts */
importScripts("vendor/precache.js");

const { versione, file } = self.PRECACHE;
const CACHE = "pdf2word-" + versione;
const CACHE_CONDIVISI = "pdf2word-condivisi";
const BASE = new URL("./", self.location).href;

// Nessuna origine esterna: script, connessioni, worker, immagini solo da 'self'.
// 'unsafe-eval' e 'wasm-unsafe-eval' servono a Pyodide (WebAssembly e caricamento moduli).
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval'",
  "connect-src 'self'",
  "worker-src 'self'",
  "img-src 'self' blob: data:",
  "style-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

self.addEventListener("install", (ev) => {
  ev.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(file.map((f) => new Request(f, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches
      .keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== CACHE && n !== CACHE_CONDIVISI).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

function conCSP(risposta) {
  const tipo = risposta.headers.get("content-type") || "";
  if (!/text\/html|javascript/.test(tipo)) return risposta;
  const headers = new Headers(risposta.headers);
  headers.set("Content-Security-Policy", CSP);
  headers.set("Referrer-Policy", "no-referrer");
  headers.set("X-Content-Type-Options", "nosniff");
  return new Response(risposta.body, { status: risposta.status, statusText: risposta.statusText, headers });
}

async function riceviCondiviso(richiesta) {
  const dati = await richiesta.formData();
  const pdf = dati.get("pdf");
  if (pdf && typeof pdf !== "string") {
    const c = await caches.open(CACHE_CONDIVISI);
    await c.put(
      "condiviso.pdf",
      new Response(pdf, { headers: { "Content-Type": "application/pdf", "X-Nome-File": encodeURIComponent(pdf.name || "documento.pdf") } }),
    );
  }
  return Response.redirect(BASE + "?condiviso=1", 303);
}

async function dallaCache(richiesta) {
  const c = await caches.open(CACHE);
  const url = new URL(richiesta.url);
  // La pagina con parametri (?condiviso=1) è sempre index.html.
  const chiave = richiesta.mode === "navigate" ? BASE : richiesta;
  const trovata = await c.match(chiave, { ignoreSearch: url.origin === self.location.origin && richiesta.mode === "navigate" });
  if (trovata) return conCSP(trovata);
  return conCSP(await fetch(richiesta));
}

self.addEventListener("fetch", (ev) => {
  const r = ev.request;
  const url = new URL(r.url);
  if (url.origin !== self.location.origin) return; // mai usato: la CSP blocca comunque le richieste esterne
  if (r.method === "POST" && url.href.startsWith(BASE + "condividi")) {
    ev.respondWith(riceviCondiviso(r));
    return;
  }
  if (r.method === "GET") ev.respondWith(dallaCache(r));
});
