// UI: registers the service worker (offline cache + CSP), starts the Web Worker
// with the engine and handles file choice, progress, password and download.
// The PDF only travels between this page and the worker: no network requests.

/* global t, applyStaticStrings */
"use strict";

const $ = (id) => document.getElementById(id);
const el = {
  light: $("engine-light"),
  engineText: $("engine-text"),
  engineNote: $("engine-note"),
  choose: $("choose"),
  file: $("file"),
  fileName: $("file-name"),
  passwordForm: $("password-form"),
  passwordLabel: $("password-label"),
  password: $("password"),
  progress: $("progress"),
  bar: $("bar"),
  progressText: $("progress-text"),
  result: $("result"),
  resultText: $("result-text"),
  download: $("download"),
  share: $("share"),
  error: $("error"),
};

const DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
let worker = null;
let engineReady = false;
let current = null; // {id, name, pdf: ArrayBuffer, start}
let docxUrl = null;
let docxFile = null;
let pending = null; // file received before the engine was ready

function show(element, visible) {
  element.hidden = !visible;
}

function engineState(text, state = "loading") {
  el.engineText.textContent = text;
  el.light.dataset.state = state;
}

function showError(msg) {
  el.error.textContent = msg;
  show(el.error, Boolean(msg));
}

function enableChoose(yes) {
  el.file.disabled = !yes;
  el.choose.setAttribute("aria-disabled", String(!yes));
}

function session(action, key) {
  try {
    return action === "get" ? sessionStorage.getItem(key) : action === "set" ? sessionStorage.setItem(key, "1") : sessionStorage.removeItem(key);
  } catch {
    return null; // storage unavailable
  }
}

// --- Service worker ---------------------------------------------------------

async function waitForServiceWorker() {
  if (!("serviceWorker" in navigator)) throw new Error(t("error.noServiceWorker"));
  const sw = navigator.serviceWorker;
  const controlled = new Promise((ok) => sw.addEventListener("controllerchange", ok, { once: true }));
  await sw.register("sw.js");
  if (sw.controller) return;
  // First run: the service worker downloads and caches the whole app.
  show(el.engineNote, true);
  engineState(t("engine.downloading"));
  await sw.ready;
  await Promise.race([controlled, new Promise((ok) => setTimeout(ok, 3000))]);
  if (sw.controller) return;
  // Service worker active but page not controlled (e.g. hard reload):
  // without it the worker would not get the CSP, so reload once.
  if (session("get", "sw-reload")) throw new Error(t("error.serviceWorkerInactive"));
  session("set", "sw-reload");
  location.reload();
  await new Promise(() => {});
}

// --- Worker -------------------------------------------------------------------

function startWorker() {
  worker = new Worker("worker.js");
  worker.onmessage = ({ data: m }) => {
    switch (m.type) {
      case "status":
        engineState(t(m.key));
        break;
      case "ready":
        engineReady = true;
        show(el.engineNote, false);
        engineState(t("engine.ready"), "ready");
        enableChoose(true);
        if (pending) {
          const f = pending;
          pending = null;
          convert(f.name, f.pdf);
        }
        break;
      case "progress":
        if (current?.id === m.id) progress(m);
        break;
      case "result":
        if (current?.id === m.id) result(m.docx);
        break;
      case "password":
        if (current?.id === m.id) askPassword(m.wrong);
        break;
      case "error":
        if (m.startup) {
          engineState(t("engine.unavailable"), "error");
          finish(t("error.engineStart", { message: m.message }));
        } else if (current?.id === m.id) {
          finish(t("error.generic", { message: m.message }));
        }
        break;
    }
  };
  worker.onerror = (e) => {
    engineState(t("engine.unavailable"), "error");
    finish(t("error.engine", { message: e.message || "?" }));
  };
}

// --- Conversion ----------------------------------------------------------------

function docxName(name) {
  return (name.replace(/\.pdf$/i, "") || "document") + ".docx";
}

function isPdf(buf) {
  const head = new Uint8Array(buf, 0, Math.min(1024, buf.byteLength));
  return new TextDecoder("latin1").decode(head).includes("%PDF-");
}

function convert(name, pdf, password) {
  showError("");
  show(el.result, false);
  show(el.passwordForm, false);
  el.fileName.textContent = name;
  show(el.fileName, true);
  if (!isPdf(pdf)) {
    showError(t("error.notPdf"));
    return;
  }
  if (!engineReady) {
    pending = { name, pdf };
    el.fileName.textContent = t("file.waiting", { name });
    return;
  }
  current = { id: (current?.id ?? 0) + 1, name, pdf, start: performance.now() };
  enableChoose(false);
  el.bar.value = 0;
  el.progressText.textContent = t("progress.opening");
  show(el.progress, true);
  // Copy: the original buffer is needed if we must retry with a password.
  const copy = pdf.slice(0);
  worker.postMessage({ type: "convert", id: current.id, pdf: copy, password }, [copy]);
}

function progress({ done, total, phase }) {
  // Parsing = 80% of the work, writing the DOCX = 20%.
  const share = phase === "parse" ? (done / total) * 80 : 80 + (done / total) * 20;
  el.bar.value = Math.round(share);
  el.progressText.textContent = t(phase === "parse" ? "progress.parse" : "progress.write", { done, total });
}

function result(docx) {
  const seconds = ((performance.now() - current.start) / 1000).toFixed(1);
  const name = docxName(current.name);
  if (docxUrl) URL.revokeObjectURL(docxUrl);
  docxFile = new File([docx], name, { type: DOCX_MIME });
  docxUrl = URL.createObjectURL(docxFile);
  el.download.href = docxUrl;
  el.download.download = name;
  el.resultText.textContent = t("result.done", { seconds, name, kb: (docx.byteLength / 1024).toFixed(0) });
  show(el.share, Boolean(navigator.canShare?.({ files: [docxFile] })));
  show(el.result, true);
  finish();
}

function askPassword(wrong) {
  el.passwordLabel.textContent = t(wrong ? "password.wrong" : "password.label");
  el.passwordForm.dataset.wrong = String(wrong);
  show(el.progress, false);
  show(el.passwordForm, true);
  el.password.value = "";
  el.password.focus();
}

function finish(errorMsg) {
  show(el.progress, false);
  if (errorMsg) showError(errorMsg);
  enableChoose(engineReady);
  el.file.value = "";
}

// --- PDF shared from another app (Web Share Target) ------------------------------

async function readShared() {
  if (!new URLSearchParams(location.search).has("shared")) return;
  history.replaceState(null, "", location.pathname);
  const cache = await caches.open("pdf2word-shared");
  const key = new URL("shared.pdf", document.baseURI).href;
  const r = await cache.match(key);
  if (!r) return;
  await cache.delete(key); // no copy stays in the browser
  const name = decodeURIComponent(r.headers.get("X-File-Name") || "document.pdf");
  convert(name, await r.arrayBuffer());
}

// --- Events ---------------------------------------------------------------------

el.file.addEventListener("change", async () => {
  const f = el.file.files?.[0];
  if (f) convert(f.name, await f.arrayBuffer());
});

el.passwordForm.addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (current) convert(current.name, current.pdf, el.password.value);
});

el.share.addEventListener("click", () => {
  navigator.share({ files: [docxFile], title: docxFile.name }).catch(() => {});
});

(async () => {
  applyStaticStrings();
  try {
    await waitForServiceWorker();
    session("remove", "sw-reload");
    engineState(t("engine.starting"));
    startWorker();
    await readShared();
  } catch (e) {
    engineState(t("engine.startFailed"), "error");
    showError(e.message || String(e));
  }
})();
