// End-to-end test of the PWA in headless Chrome (puppeteer-core + installed Chrome).
//
// Prerequisites: web/vendor/ prepared (scripts/prepare_vendor.py) and web/ served, e.g.
//   python3 -m http.server 8080 --bind 127.0.0.1 --directory web
// Usage:
//   node tests/e2e_pwa.mjs http://127.0.0.1:8080/ <pdf_dir> <docx_out_dir> [chrome_path]
//
// Checks:
//  1. engine start-up and conversion of every PDF in the folder via the file picker,
//     with a real download of the DOCX;
//  2. no request to origins other than the app's;
//  3. the CSP blocks fetches to other sites (page and worker);
//  4. protected PDF: password prompt, wrong password, right password;
//  5. shared PDF (simulated POST to ./share, as Android does);
//  6. offline mode: reload and convert without network;
//  7. UI language follows the browser (English / Italian);
//  8. diagnostic report: valid JSON with layout only, no document text;
//  9. build label in the footer, long file names fit a phone-width screen.

import { createRequire } from "node:module";
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, unlinkSync } from "node:fs";
import { join, resolve } from "node:path";

const require = createRequire(join(resolve("tests"), "package.json"));
const puppeteer = require("puppeteer-core");

const [base, pdfDir, outDir, chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] =
  process.argv.slice(2);
if (!base || !pdfDir || !outDir) {
  console.error("Usage: node tests/e2e_pwa.mjs <base_url> <pdf_dir> <docx_out_dir> [chrome]");
  process.exit(2);
}
const ORIGIN = new URL(base).origin;
const ENGINE_TIMEOUT = 5 * 60_000;
const CONVERSION_TIMEOUT = 3 * 60_000;
const PASSWORD = "test"; // see spike/make_test_pdfs.py
mkdirSync(outDir, { recursive: true });

let failures = 0;
const ok = (msg) => console.log(`OK   ${msg}`);
const fail = (msg) => {
  failures++;
  console.error(`FAIL ${msg}`);
};

// On CI (Ubuntu 24.04) AppArmor blocks Chrome's sandbox: disable it there.
const args = ["--no-first-run", "--lang=en-US", ...(process.env.CI ? ["--no-sandbox"] : [])];
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args });
const page = await browser.newPage();
const external = [];
page.on("request", (r) => {
  const u = r.url();
  // example.org is the CSP probe: it must be blocked, it does not count as a leak.
  if (!u.startsWith(ORIGIN) && !u.startsWith("blob:") && !u.startsWith("data:") && !u.startsWith("https://example.org/")) external.push(u);
});
page.on("console", (m) => {
  if (m.type() === "error") console.log(`  [console] ${m.text()}`);
});

async function waitForEngine(p = page) {
  await p.waitForSelector('#engine-light[data-state="ready"], #engine-light[data-state="error"]', { timeout: ENGINE_TIMEOUT });
  const state = await p.$eval("#engine-light", (e) => e.dataset.state);
  if (state !== "ready") throw new Error("engine error: " + (await p.$eval("#error", (e) => e.textContent)));
}

// Wait for the end of a conversion: result, password prompt or error.
async function waitForOutcome() {
  await page.waitForFunction(
    () => !document.getElementById("result").hidden || !document.getElementById("password-form").hidden || !document.getElementById("error").hidden,
    { timeout: CONVERSION_TIMEOUT },
  );
  return page.evaluate(() => ({
    result: !document.getElementById("result").hidden,
    password: !document.getElementById("password-form").hidden,
    wrong: document.getElementById("password-form").dataset.wrong === "true",
    error: document.getElementById("error").hidden ? null : document.getElementById("error").textContent,
    text: document.getElementById("result-text").textContent,
  }));
}

// Real download: click "Download DOCX", as the user would.
// (The blob cannot be read with fetch: the CSP connect-src 'self' blocks it.)
const cdp = await page.createCDPSession();
await cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: resolve(outDir), eventsEnabled: true });

async function downloadDocx(name) {
  const path = join(resolve(outDir), name);
  if (existsSync(path)) unlinkSync(path);
  const done = new Promise((res, rej) => {
    const h = (e) => {
      if (e.state === "completed") { cdp.off("Browser.downloadProgress", h); res(); }
      if (e.state === "canceled") { cdp.off("Browser.downloadProgress", h); rej(new Error("download canceled")); }
    };
    cdp.on("Browser.downloadProgress", h);
  });
  await page.click("#download");
  await done;
  return readFileSync(path);
}

async function convertFile(path) {
  await page.evaluate(() => {
    document.getElementById("result").hidden = true;
    document.getElementById("error").hidden = true;
  });
  const input = await page.$("#file");
  await input.uploadFile(path);
  return waitForOutcome();
}

try {
  // 1. Start-up
  const t0 = performance.now();
  await page.goto(base, { waitUntil: "load" });
  await waitForEngine();
  ok(`engine ready in ${((performance.now() - t0) / 1000).toFixed(1)}s (first run, with download and caching)`);

  // 1b. Convert every PDF
  const pdfs = readdirSync(pdfDir).filter((n) => n.endsWith(".pdf") && !n.startsWith("protected")).sort();
  for (const n of pdfs) {
    const r = await convertFile(resolve(pdfDir, n));
    if (r.result) {
      const data = await downloadDocx(n.replace(/\.pdf$/, ".docx"));
      data.subarray(0, 2).toString() === "PK" ? ok(`${n}: ${r.text}`) : fail(`${n}: the output is not a DOCX`);
    } else fail(`${n}: ${r.error ?? "no outcome"}`);
  }

  // 1c. Diagnostic report: valid JSON, layout only, none of the document's words
  {
    const invoice = pdfs.find((n) => n.includes("invoice")) ?? pdfs[0];
    await convertFile(resolve(pdfDir, invoice));
    // Stub the share sheet to capture what would be shared.
    await page.evaluate(() => {
      navigator.share = async (data) => {
        window.__shared = data;
      };
    });
    await page.click("#diag-button");
    await page.waitForFunction(() => document.getElementById("diag-text").value.startsWith("{"), { timeout: CONVERSION_TIMEOUT });
    const text = await page.$eval("#diag-text", (e) => e.value);
    let report = null;
    try {
      report = JSON.parse(text);
    } catch {
      fail("diagnostics: report is not valid JSON");
    }
    if (report) {
      // Distinctive words from spike/make_test_pdfs.py documents.
      const leaked = ["ACME", "Faketown", "Testville", "Example", "INVOICE", "Supplier", "Beta Testing", "IBAN"]
        .filter((w) => text.includes(w));
      report.pdf?.pages >= 1 && Array.isArray(report.docx?.body)
        ? ok(`diagnostics: ${invoice} -> ${text.length} chars, ${report.docx.body.length} DOCX items`)
        : fail("diagnostics: report missing pdf/docx sections");
      leaked.length === 0 ? ok("diagnostics: no document text in the report") : fail(`diagnostics: leaked ${leaked.join(", ")}`);
      await page.click("#diag-share");
      const sharedText = await page.evaluate(() => window.__shared?.text ?? null);
      sharedText === text ? ok("diagnostics: share button sends the report") : fail("diagnostics: share button did not send the report");
    }
  }

  // 3. CSP: the page cannot reach other sites
  const externalFetch = await page.evaluate(() =>
    fetch("https://example.org/", { mode: "no-cors" }).then(() => "open", () => "blocked"),
  );
  externalFetch === "blocked" ? ok("page CSP: external fetch blocked") : fail("page CSP: external fetch NOT blocked");
  const workerCsp = await page.evaluate(async () => (await fetch("worker.js")).headers.get("content-security-policy") || "");
  /connect-src 'self'/.test(workerCsp) ? ok("worker CSP: served with connect-src 'self'") : fail("worker CSP missing");

  // 4. Protected PDF
  for (const n of readdirSync(pdfDir).filter((x) => x.startsWith("protected") && x.endsWith(".pdf"))) {
    let r = await convertFile(resolve(pdfDir, n));
    if (!r.password) fail(`${n}: no password prompt`);
    else {
      await page.type("#password", "wrong-password");
      await page.click("#password-form button");
      r = await waitForOutcome();
      r.password && r.wrong ? ok(`${n}: wrong password detected`) : fail(`${n}: wrong password not handled`);
      await page.type("#password", PASSWORD);
      await page.click("#password-form button");
      r = await waitForOutcome();
      r.result ? ok(`${n}: unlocked and converted`) : fail(`${n}: ${r.error ?? "not converted"}`);
    }
  }

  // 5. Shared from another app (multipart POST, as Android does)
  const shared = pdfs[0];
  if (shared) {
    const b64 = readFileSync(resolve(pdfDir, shared)).toString("base64");
    const status = await page.evaluate(async (b64, name) => {
      const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const fd = new FormData();
      fd.append("pdf", new File([bin], name, { type: "application/pdf" }));
      const r = await fetch("share", { method: "POST", body: fd, redirect: "manual" });
      return r.type === "opaqueredirect" ? 303 : r.status;
    }, b64, shared);
    await page.goto(new URL("?shared=1", base).href, { waitUntil: "load" });
    await waitForEngine();
    const r = await waitForOutcome();
    const name = await page.$eval("#file-name", (e) => e.textContent);
    r.result && name === shared
      ? ok(`share: ${shared} received (POST -> ${status}) and converted`)
      : fail(`share: ${r.error ?? "no outcome"} (POST -> ${status}, name="${name}")`);
    const left = await page.evaluate(async () => (await (await caches.open("pdf2word-shared")).keys()).length);
    left === 0 ? ok("share: no copy left in the cache") : fail(`share: ${left} files left in the cache`);
  }

  // 6. Offline
  await page.setOfflineMode(true);
  const t1 = performance.now();
  await page.reload({ waitUntil: "load" });
  await waitForEngine();
  ok(`offline: engine ready in ${((performance.now() - t1) / 1000).toFixed(1)}s from the cache`);
  if (pdfs[1] ?? pdfs[0]) {
    const r = await convertFile(resolve(pdfDir, pdfs[1] ?? pdfs[0]));
    r.result ? ok(`offline: ${r.text}`) : fail(`offline: ${r.error ?? "no outcome"}`);
  }
  await page.setOfflineMode(false);

  // 7. UI language
  const en = await page.$eval("h1", (e) => e.textContent);
  en === "PDF to Word" ? ok(`language: English UI ("${en}")`) : fail(`language: expected English, got "${en}"`);
  const itPage = await browser.newPage();
  await itPage.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, "languages", { get: () => ["it-IT", "it"] });
  });
  await itPage.goto(base, { waitUntil: "load" });
  const it = await itPage.$eval("h1", (e) => e.textContent);
  it === "PDF in Word" ? ok(`language: Italian UI ("${it}")`) : fail(`language: expected Italian, got "${it}"`);
  await itPage.close();
  // Regression: English first, Italian only as a secondary language -> English.
  const mixedPage = await browser.newPage();
  await mixedPage.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, "languages", { get: () => ["en-US", "en", "it-IT"] });
  });
  await mixedPage.goto(base, { waitUntil: "load" });
  const mixed = await mixedPage.$eval("h1", (e) => e.textContent);
  mixed === "PDF to Word" ? ok("language: English preferred over secondary Italian") : fail(`language: en-US first gave "${mixed}"`);
  await mixedPage.close();

  // 9. Build label and phone-width layout with a very long file name
  const build = await page.$eval("#build", (e) => e.textContent);
  /^build [0-9a-f]{12}$/.test(build) ? ok(`footer shows "${build}"`) : fail(`build label: "${build}"`);
  if (pdfs[0]) {
    const longName = "a_very_long_file_name_without_spaces_that_used_to_overflow_the_phone_screen_" + "x".repeat(60) + ".pdf";
    const longPath = join(resolve(outDir), longName);
    copyFileSync(resolve(pdfDir, pdfs[0]), longPath);
    await page.setViewport({ width: 360, height: 800, isMobile: true });
    const r = await convertFile(longPath);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    r.result && overflow <= 0 ? ok("long file name fits a 360 px screen") : fail(`long file name overflows by ${overflow}px`);
    unlinkSync(longPath);
  }

  // 2. No external requests
  external.length === 0 ? ok("no requests to other sites") : fail(`external requests: ${[...new Set(external)].join(", ")}`);
} catch (e) {
  fail(String(e?.stack ?? e));
} finally {
  await browser.close();
}
process.exit(failures ? 1 : 0);
