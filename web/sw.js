// Service worker:
// - caches the whole app (Pyodide included) for offline use;
// - serves page and worker with a Content-Security-Policy that forbids connections
//   to other sites (connect-src 'self'): the PDF cannot leave the device;
// - receives PDFs shared from other Android apps (Web Share Target).

/* global importScripts */
importScripts("vendor/precache.js");

const { version, files } = self.PRECACHE;
const CACHE = "pdf2word-" + version;
const SHARED_CACHE = "pdf2word-shared";
const BASE = new URL("./", self.location).href;

// No external origins: scripts, connections, workers, images only from 'self'.
// 'unsafe-eval' and 'wasm-unsafe-eval' are needed by Pyodide (WebAssembly and module loading).
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
      .then((c) => c.addAll(files.map((f) => new Request(f, { cache: "reload" }))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE && n !== SHARED_CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

function withCsp(response) {
  const type = response.headers.get("content-type") || "";
  if (!/text\/html|javascript/.test(type)) return response;
  const headers = new Headers(response.headers);
  headers.set("Content-Security-Policy", CSP);
  headers.set("Referrer-Policy", "no-referrer");
  headers.set("X-Content-Type-Options", "nosniff");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

async function receiveShared(request) {
  const data = await request.formData();
  const pdf = data.get("pdf");
  if (pdf && typeof pdf !== "string") {
    const c = await caches.open(SHARED_CACHE);
    await c.put(
      "shared.pdf",
      new Response(pdf, { headers: { "Content-Type": "application/pdf", "X-File-Name": encodeURIComponent(pdf.name || "document.pdf") } }),
    );
  }
  return Response.redirect(BASE + "?shared=1", 303);
}

async function fromCache(request) {
  const c = await caches.open(CACHE);
  // Navigations (including ?shared=1) always get the cached index page.
  const hit = await c.match(request.mode === "navigate" ? BASE : request);
  if (hit) return withCsp(hit);
  return withCsp(await fetch(request));
}

self.addEventListener("fetch", (ev) => {
  const r = ev.request;
  const url = new URL(r.url);
  if (url.origin !== self.location.origin) return; // never used: the CSP blocks external requests anyway
  if (r.method === "POST" && url.href.startsWith(BASE + "share")) {
    ev.respondWith(receiveShared(r));
    return;
  }
  if (r.method === "GET") ev.respondWith(fromCache(r));
});
