"use strict";
/*
 * zcode-hud main-process loader (v0.2).
 *
 * Injected into ZCode's ESM main entry by scripts/install.py as a single
 * dynamic import line.  Responsibilities:
 *   1. inject theme.css into every BrowserWindow;
 *   2. chain-load the vendored zusage statusbar loader (../zusage), which
 *      provides the animated usage bar, per-answer rate line and context
 *      ring, backed by a trigger-driven resident python query process.
 *
 * The vendored runtime is upstream ByteRax/zcode-token-usage-statusbar
 * (MIT, see vendor/UPSTREAM.md).  Its config.json disables quota queries
 * and auto-update; no plugin hooks are registered, so there is no second
 * asar patch point and no self-repair.
 */

const path = require("path");
const fs = require("fs");
const { app, BrowserWindow } = require("electron");

const HERE = __dirname;
const CSS_FILE = path.join(HERE, "theme.css");
const ZUSAGE_LOADER = path.join(HERE, "..", "zusage", "inject-main.cjs");

const log = (...args) => console.error("[zcode-hud]", ...args);

// The vendored loader force-opens CDP port 9229 unless this env is set.
// The statusbar injects via webContents and does not need the debug port.
process.env.ZCODE_DISABLE_FIXED_REMOTE_DEBUGGING_PORT = "1";

const cssKeys = new Map(); // webContents.id -> insertCSS key

function inject(wc) {
  if (!wc || wc.isDestroyed()) return;
  const oldKey = cssKeys.get(wc.id);
  if (oldKey) {
    try {
      const pending = wc.removeInsertedCSS(oldKey);
      if (pending && typeof pending.catch === "function") pending.catch(() => {});
    } catch (_) { /* ignore */ }
    cssKeys.delete(wc.id);
  }
  try {
    const css = fs.readFileSync(CSS_FILE, "utf8");
    wc.insertCSS(css, { cssOrigin: "user" })
      .then((key) => cssKeys.set(wc.id, key))
      .catch((err) => log("insertCSS failed:", err.message));
  } catch (err) {
    log("read theme.css failed:", err.message);
  }
}

function attach(wc) {
  if (!wc || wc.isDestroyed()) return;
  wc.on("did-finish-load", () => inject(wc));
  if (!wc.isLoading() && wc.getURL()) inject(wc);
  wc.on("destroyed", () => cssKeys.delete(wc.id));
}

app.on("web-contents-created", (_event, wc) => {
  try {
    if (wc.getType() === "window") attach(wc);
  } catch (_) { /* ignore */ }
});

app.whenReady().then(() => {
  for (const win of BrowserWindow.getAllWindows()) attach(win.webContents);
}).catch((err) => log("ready hook failed:", err.message));

// Chain-load the statusbar loader.  It registers its own ready hooks and
// window listeners; requiring it here keeps the original injection timing
// (entry-tail, before app ready).
try {
  require(ZUSAGE_LOADER);
  log("statusbar loader loaded:", ZUSAGE_LOADER);
} catch (err) {
  log("statusbar loader failed:", err.message);
}