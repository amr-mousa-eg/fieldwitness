// Dev helper (T9.7, needs a local Chrome; CHROME=<path> if elsewhere). Drives the app with real key
// events only (Tab, Enter, Escape) and checks: skip link first; a field opens from the list; focus
// moves to the new page; field tabs and explainers work; no page overflow at 380 px.
// Usage: node scripts/keyboard-check.mjs http://localhost:5173/
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [base] = process.argv.slice(2);
const CHROME = process.env.CHROME ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";
const port = 9334;
const chrome = spawn(CHROME, [
  "--headless=new",
  "--enable-unsafe-swiftshader",
  "--use-angle=swiftshader",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "fw-kbd-"))}`,
  "about:blank",
]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 50 && !wsUrl; i++) {
  await sleep(200);
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    wsUrl = list.find((t) => t.type === "page")?.webSocketDebuggerUrl;
  } catch {}
}
if (!wsUrl) throw new Error("Chrome did not start");
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
const send = (method, params = {}) =>
  new Promise((r) => {
    pending.set(++id, r);
    ws.send(JSON.stringify({ id, method, params }));
  });
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true })).result?.result?.value;
const KEYS = { Tab: 9, Enter: 13, Escape: 27 };
async function press(key, shift = false) {
  const p = { key, code: key, windowsVirtualKeyCode: KEYS[key], modifiers: shift ? 8 : 0 };
  await send("Input.dispatchKeyEvent", { type: "rawKeyDown", ...p });
  if (key === "Enter") await send("Input.dispatchKeyEvent", { type: "char", text: "\r", ...p });
  await send("Input.dispatchKeyEvent", { type: "keyUp", ...p });
  await sleep(60);
}
const active = () =>
  evaluate(`(() => { const a = document.activeElement; return a ? (a.tagName + "|" + (a.className || "") + "|" + (a.id || "") + "|" + (a.textContent || "").trim().slice(0, 40)) : "" })()`);
async function waitFor(selector) {
  for (let i = 0; i < 100; i++) {
    if (await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`)) return true;
    await sleep(100);
  }
  return false;
}
/** Tab forward until `test(activeDescriptor)` is true; returns the number of presses or -1. */
async function tabUntil(test, max = 80) {
  for (let i = 1; i <= max; i++) {
    await press("Tab");
    if (test(await active())) return i;
  }
  return -1;
}

const results = [];
const check = (name, ok, detail = "") => results.push(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ` (${detail})` : ""}`);

await send("Runtime.enable");
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 380, height: 800, deviceScaleFactor: 1, mobile: true });
await send("Emulation.setFocusEmulationEnabled", { enabled: true }); // headless pages are not focused otherwise
await send("Page.navigate", { url: base });
await waitFor(".field-item");

await press("Tab");
const first = await active();
check("first Tab reaches the skip link", first.includes("skip-link"), first);
await press("Enter");
check("skip link focuses main", (await active()).startsWith("MAIN|"));

const n = await tabUntil((a) => a.includes("field-item"));
check("Tab reaches a field in the list", n > 0, `${n} presses`);
await press("Enter");
check("Enter opens the field", await waitFor(".field-page .tabs"));
await sleep(200);
check("focus moves to the new page", (await active()).startsWith("MAIN|"));

const t2 = await tabUntil((a) => a.startsWith("A|") && a.endsWith("|Options"));
check("Tab reaches the Options tab", t2 > 0, `${t2} presses`);
await press("Enter");
check("Enter shows the options", await waitFor("table.options"));

const t3 = await tabUntil((a) => a.includes("explain-btn"));
check("Tab reaches an explainer button", t3 > 0, `${t3} presses`);
await press("Enter");
check("Enter opens the explainer", await waitFor(".explain-pop"));
await press("Escape");
await sleep(100);
check(
  "Escape closes it and keeps focus on its button",
  !(await evaluate(`!!document.querySelector(".explain-pop")`)) && (await active()).includes("explain-btn"),
);

const t4 = await tabUntil((a) => a.startsWith("BUTTON|") && a.includes("Show details"));
check("Tab reaches a details button", t4 > 0, `${t4} presses`);
await press("Enter");
check("Enter opens the option details", await waitFor(".detail-row"));

check("no horizontal page scroll at 380 px", await evaluate("document.documentElement.scrollWidth <= innerWidth"));

console.log(results.join("\n"));
ws.close();
chrome.kill();
process.exit(results.some((r) => r.startsWith("FAIL")) ? 1 : 0);
