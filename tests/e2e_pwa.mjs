// Test end-to-end della PWA in Chrome headless (puppeteer-core + Chrome installato).
//
// Prerequisiti: web/vendor/ preparato (scripts/prepara_vendor.py) e web/ servito, es.
//   python3 -m http.server 8080 --bind 127.0.0.1 --directory web
// Uso:
//   node tests/e2e_pwa.mjs http://127.0.0.1:8080/ <cartella_pdf> <cartella_docx_out> [percorso_chrome]
//
// Verifica:
//  1. avvio del motore e conversione di ogni PDF della cartella dal selettore file;
//  2. nessuna richiesta verso origini diverse da quella dell'app;
//  3. la CSP blocca fetch verso altri siti (pagina e worker);
//  4. PDF protetto: richiesta password, password errata, password giusta;
//  5. PDF condiviso (POST simulato a ./condividi, come fa Android);
//  6. modalità offline: ricarica e conversione senza rete.

import { createRequire } from "node:module";
import { existsSync, mkdirSync, readdirSync, readFileSync, unlinkSync } from "node:fs";
import { join, resolve } from "node:path";

const require = createRequire(join(resolve("tests"), "package.json"));
const puppeteer = require("puppeteer-core");

const [base, pdfDir, outDir, chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] =
  process.argv.slice(2);
if (!base || !pdfDir || !outDir) {
  console.error("Uso: node tests/e2e_pwa.mjs <url_base> <cartella_pdf> <cartella_docx_out> [chrome]");
  process.exit(2);
}
const ORIGINE = new URL(base).origin;
const TIMEOUT_MOTORE = 5 * 60_000;
const TIMEOUT_CONVERSIONE = 3 * 60_000;
mkdirSync(outDir, { recursive: true });

let fallimenti = 0;
const ok = (msg) => console.log(`OK   ${msg}`);
const ko = (msg) => {
  fallimenti++;
  console.error(`FAIL ${msg}`);
};

// In CI (Ubuntu 24.04) il sandbox di Chrome è bloccato da AppArmor: lì si disattiva.
const args = ["--no-first-run", ...(process.env.CI ? ["--no-sandbox"] : [])];
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args });
const page = await browser.newPage();
const esterne = [];
page.on("request", (r) => {
  const u = r.url();
  // example.org è la sonda del test CSP: deve risultare bloccata, non conta come fuga.
  if (!u.startsWith(ORIGINE) && !u.startsWith("blob:") && !u.startsWith("data:") && !u.startsWith("https://example.org/")) esterne.push(u);
});
page.on("console", (m) => {
  if (m.type() === "error") console.log(`  [console] ${m.text()}`);
});

async function attendiMotore() {
  await page.waitForSelector('#spia-motore[data-stato="pronto"], #spia-motore[data-stato="errore"]', { timeout: TIMEOUT_MOTORE });
  const stato = await page.$eval("#spia-motore", (e) => e.dataset.stato);
  if (stato !== "pronto") throw new Error("motore in errore: " + (await page.$eval("#errore", (e) => e.textContent)));
}

// Attende la fine della conversione: esito, richiesta password o errore.
async function attendiFine() {
  await page.waitForFunction(
    () => !document.getElementById("esito").hidden || !document.getElementById("form-password").hidden || !document.getElementById("errore").hidden,
    { timeout: TIMEOUT_CONVERSIONE },
  );
  return page.evaluate(() => ({
    esito: !document.getElementById("esito").hidden,
    password: !document.getElementById("form-password").hidden,
    errore: document.getElementById("errore").hidden ? null : document.getElementById("errore").textContent,
    testo: document.getElementById("testo-esito").textContent,
  }));
}

// Download reale: clic su "Scarica DOCX", come farebbe l'utente.
// (Non si può leggere il blob con fetch: la CSP connect-src 'self' lo blocca.)
const cdp = await page.createCDPSession();
await cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: resolve(outDir), eventsEnabled: true });

async function salvaDocx(nome) {
  const percorso = join(resolve(outDir), nome);
  if (existsSync(percorso)) unlinkSync(percorso);
  const finito = new Promise((ok, no) => {
    const h = (e) => {
      if (e.state === "completed") { cdp.off("Browser.downloadProgress", h); ok(); }
      if (e.state === "canceled") { cdp.off("Browser.downloadProgress", h); no(new Error("download annullato")); }
    };
    cdp.on("Browser.downloadProgress", h);
  });
  await page.click("#scarica");
  await finito;
  return readFileSync(percorso);
}

async function convertiFile(percorso) {
  await page.evaluate(() => {
    document.getElementById("esito").hidden = true;
    document.getElementById("errore").hidden = true;
  });
  const input = await page.$("#file");
  await input.uploadFile(percorso);
  return attendiFine();
}

try {
  // 1. Avvio
  const t0 = performance.now();
  await page.goto(base, { waitUntil: "load" });
  await attendiMotore();
  ok(`motore pronto in ${((performance.now() - t0) / 1000).toFixed(1)}s (primo avvio, con download e cache)`);

  // 1b. Conversione di ogni PDF
  const pdfs = readdirSync(pdfDir).filter((n) => n.endsWith(".pdf") && !n.startsWith("protetto")).sort();
  for (const n of pdfs) {
    const r = await convertiFile(resolve(pdfDir, n));
    if (r.esito) {
      const dati = await salvaDocx(n.replace(/\.pdf$/, ".docx"));
      dati.subarray(0, 2).toString() === "PK" ? ok(`${n}: ${r.testo}`) : ko(`${n}: il risultato non è un DOCX`);
    } else ko(`${n}: ${r.errore ?? "nessun esito"}`);
  }

  // 3. CSP: la pagina non può contattare altri siti
  const fetchEsterna = await page.evaluate(() =>
    fetch("https://example.org/", { mode: "no-cors" }).then(() => "aperto", () => "bloccato"),
  );
  fetchEsterna === "bloccato" ? ok("CSP pagina: fetch esterna bloccata") : ko("CSP pagina: fetch esterna NON bloccata");
  const cspWorker = await page.evaluate(async () => {
    const r = await fetch("worker.js");
    return r.headers.get("content-security-policy") || "";
  });
  /connect-src 'self'/.test(cspWorker) ? ok("CSP worker: servito con connect-src 'self'") : ko("CSP worker mancante");

  // 4. PDF protetto
  const protetti = readdirSync(pdfDir).filter((n) => n.startsWith("protetto") && n.endsWith(".pdf"));
  for (const n of protetti) {
    let r = await convertiFile(resolve(pdfDir, n));
    if (!r.password) ko(`${n}: password non richiesta`);
    else {
      await page.type("#password", "sbagliata");
      await page.click("#form-password button");
      r = await attendiFine();
      const etichetta = await page.$eval("#etichetta-password", (e) => e.textContent);
      r.password && /errata/i.test(etichetta) ? ok(`${n}: password errata riconosciuta`) : ko(`${n}: password errata non gestita`);
      await page.type("#password", "prova");
      await page.click("#form-password button");
      r = await attendiFine();
      r.esito ? ok(`${n}: sbloccato e convertito`) : ko(`${n}: ${r.errore ?? "non convertito"}`);
    }
  }

  // 5. Condivisione da altra app (POST multipart come Android)
  const condiviso = pdfs[0];
  if (condiviso) {

    const b64 = readFileSync(resolve(pdfDir, condiviso)).toString("base64");
    const stato = await page.evaluate(async (b64, nome) => {
      const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const fd = new FormData();
      fd.append("pdf", new File([bin], nome, { type: "application/pdf" }));
      const r = await fetch("condividi", { method: "POST", body: fd, redirect: "manual" });
      return r.type === "opaqueredirect" ? 303 : r.status;
    }, b64, condiviso);
    await page.goto(new URL("?condiviso=1", base).href, { waitUntil: "load" });
    await attendiMotore();
    const r = await attendiFine();
    const nome = await page.$eval("#nome-file", (e) => e.textContent);
    r.esito && nome === condiviso
      ? ok(`condivisione: ${condiviso} ricevuto (POST -> ${stato}) e convertito`)
      : ko(`condivisione: ${r.errore ?? "nessun esito"} (POST -> ${stato}, nome="${nome}")`);
    const resti = await page.evaluate(async () => (await (await caches.open("pdf2word-condivisi")).keys()).length);
    resti === 0 ? ok("condivisione: nessuna copia rimasta in cache") : ko(`condivisione: ${resti} file rimasti in cache`);
  }

  // 6. Offline
  await page.setOfflineMode(true);
  const t1 = performance.now();
  await page.reload({ waitUntil: "load" });
  await attendiMotore();
  ok(`offline: motore pronto in ${((performance.now() - t1) / 1000).toFixed(1)}s dalla cache`);
  if (pdfs[1] ?? pdfs[0]) {
    const r = await convertiFile(resolve(pdfDir, pdfs[1] ?? pdfs[0]));
    r.esito ? ok(`offline: ${r.testo}`) : ko(`offline: ${r.errore ?? "nessun esito"}`);
  }
  await page.setOfflineMode(false);

  // 2. Nessuna richiesta esterna
  esterne.length === 0 ? ok("nessuna richiesta verso altri siti") : ko(`richieste esterne: ${[...new Set(esterne)].join(", ")}`);
} catch (e) {
  ko(String(e?.stack ?? e));
} finally {
  await browser.close();
}
process.exit(fallimenti ? 1 : 0);
