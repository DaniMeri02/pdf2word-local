// UI strings. Language follows the device: Italian if the browser prefers it, English otherwise.
// Static text in index.html uses data-i18n="key"; scripts use t("key", {vars}).

"use strict";

const STRINGS = {
  en: {
    "app.title": "PDF to Word",
    "app.subtitle": "Converted on your device: the file never leaves your phone.",
    "engine.preparing": "Preparing…",
    "engine.firstRun": "First run only: about 45 MB is downloaded, then the app also works offline.",
    "engine.downloading": "Downloading the app for offline use…",
    "engine.starting": "Starting the engine…",
    "engine.startingPython": "Starting Python…",
    "engine.loadingLibraries": "Loading libraries…",
    "engine.loadingEngine": "Loading the conversion engine…",
    "engine.ready": "Ready, works offline",
    "engine.unavailable": "Engine unavailable",
    "engine.startFailed": "Start-up failed",
    "file.choose": "Choose PDF",
    "file.waiting": "{name} — waiting for the engine…",
    "password.label": "This PDF is protected: enter the password",
    "password.wrong": "Wrong password, try again",
    "password.unlock": "Unlock",
    "progress.opening": "Opening the document…",
    "progress.parse": "Analysing page {done} of {total}",
    "progress.write": "Writing page {done} of {total}",
    "result.done": "Done in {seconds} s: {name} ({kb} KB)",
    "result.download": "Download DOCX",
    "result.openWith": "Open with…",
    "result.tip": "In Word for Android, switch to Print Layout to see the real page instead of the mobile view.",
    "error.notPdf": "The selected file doesn't look like a PDF.",
    "error.generic": "Error: {message}",
    "error.engine": "Engine error: {message}",
    "error.engineStart": "Could not start the engine: {message}",
    "error.noServiceWorker": "This browser doesn't support service workers: use an up-to-date Chrome.",
    "error.serviceWorkerInactive": "Service worker not active: reload the page normally.",
    "diag.button": "Something looks wrong? Create a diagnostic report",
    "diag.working": "Preparing the report…",
    "diag.note": "The report contains only layout data (page sizes, positions, font names and sizes, table shapes) and the software that produced the PDF. No text and no images. Check it before sharing it.",
    "diag.copy": "Copy report",
    "diag.copied": "Copied",
    "diag.error": "Could not create the report: {message}",
    "footer.digital": "Works with digital PDFs (selectable text). Scanned PDFs are not supported.",
    "footer.privacy": "No uploads, no tracking.",
    "footer.source": "Source code",
  },
  it: {
    "app.title": "PDF in Word",
    "app.subtitle": "Conversione sul dispositivo: il file non lascia mai il telefono.",
    "engine.preparing": "Preparazione…",
    "engine.firstRun": "Solo al primo avvio vengono scaricati circa 45 MB, poi l'app funziona anche offline.",
    "engine.downloading": "Download dell'app per l'uso offline…",
    "engine.starting": "Avvio del motore…",
    "engine.startingPython": "Avvio di Python…",
    "engine.loadingLibraries": "Caricamento delle librerie…",
    "engine.loadingEngine": "Caricamento del motore di conversione…",
    "engine.ready": "Pronto, anche offline",
    "engine.unavailable": "Motore non disponibile",
    "engine.startFailed": "Avvio non riuscito",
    "file.choose": "Scegli PDF",
    "file.waiting": "{name} — in attesa che il motore sia pronto…",
    "password.label": "Il PDF è protetto: inserisci la password",
    "password.wrong": "Password errata, riprova",
    "password.unlock": "Sblocca",
    "progress.opening": "Apertura del documento…",
    "progress.parse": "Analisi pagina {done} di {total}",
    "progress.write": "Scrittura pagina {done} di {total}",
    "result.done": "Fatto in {seconds} s: {name} ({kb} KB)",
    "result.download": "Scarica DOCX",
    "result.openWith": "Apri con…",
    "result.tip": "In Word per Android passa a «Layout di stampa» per vedere la pagina reale invece della vista per dispositivi mobili.",
    "error.notPdf": "Il file scelto non sembra un PDF.",
    "error.generic": "Errore: {message}",
    "error.engine": "Errore del motore: {message}",
    "error.engineStart": "Impossibile avviare il motore: {message}",
    "error.noServiceWorker": "Questo browser non supporta i service worker: usa Chrome aggiornato.",
    "error.serviceWorkerInactive": "Service worker non attivo: ricarica la pagina normalmente.",
    "diag.button": "Qualcosa non va? Crea un report di diagnostica",
    "diag.working": "Preparazione del report…",
    "diag.note": "Il report contiene solo dati di impaginazione (dimensioni delle pagine, posizioni, nomi e dimensioni dei font, struttura delle tabelle) e il software che ha prodotto il PDF. Nessun testo e nessuna immagine. Controllalo prima di condividerlo.",
    "diag.copy": "Copia report",
    "diag.copied": "Copiato",
    "diag.error": "Impossibile creare il report: {message}",
    "footer.digital": "Funziona con PDF digitali (testo selezionabile). I PDF scansionati non sono supportati.",
    "footer.privacy": "Nessun upload, nessun tracciamento.",
    "footer.source": "Codice sorgente",
  },
};

const LANG = (navigator.languages || [navigator.language || "en"]).some((l) => /^it\b/i.test(l)) ? "it" : "en";

function t(key, vars = {}) {
  const s = STRINGS[LANG][key] ?? STRINGS.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

function applyStaticStrings() {
  document.documentElement.lang = LANG;
  document.title = t("app.title");
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
}
