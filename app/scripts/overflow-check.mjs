// Dev helper (needs a local Chrome; CHROME=<path> if elsewhere). Opens every route at phone widths
// (360 and 390 px) and fails if the document is wider than the viewport (horizontal page scroll).
// For each failure it lists the elements that stick out past the right edge.
// Usage: node scripts/overflow-check.mjs http://localhost:5173/
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [base] = process.argv.slice(2);
if (!base) {
  console.error("usage: node scripts/overflow-check.mjs <app url>");
  process.exit(2);
}
const WIDTHS = [360, 390];
const REGION = "ks_t14slh";
const FIELD = "0d5615b52572c5c2eeac7fdfef8cdda167050a22"; // tour demo field (src/TourGuide.tsx)
const ROUTES = [
  `#/${REGION}/map`,
  `#/${REGION}/scoreboard`,
  `#/${REGION}/methods`,
  "#/add-field",
  ...["story", "options", "calendar", "advisor", "sim3d"].map((tab) => `#/${REGION}/${FIELD}/${tab}`),
];

const CHROME = process.env.CHROME ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";
const port = 9335;
const chrome = spawn(CHROME, [
  "--headless=new",
  "--enable-unsafe-swiftshader",
  "--use-angle=swiftshader",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "fw-ovf-"))}`,
  "--hide-scrollbars",
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
const evaluate = async (expression) =>
  (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result?.result?.value;

// Settle: wait until no loading text is left (region, field, 3D packs load one after another),
// then until the layout width has been stable for 1 s. Up to ~20 s per route.
const SETTLE = `(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const loading = () =>
    !document.querySelector("main *") ||
    /Loading (region|field|3D simulation)/.test(document.body.innerText) ||
    !!document.querySelector(".map-loading, .rail-loading-placeholder, .sim3d-loading-state");
  for (let i = 0; i < 150 && loading(); i++) await sleep(100);
  let last = -1, same = 0;
  for (let i = 0; i < 20 && same < 4; i++) {
    const w = document.documentElement.scrollWidth;
    same = w === last ? same + 1 : 0;
    last = w;
    await sleep(250);
  }
})()`;

// On a phone the layout viewport grows to fit wide content (the page then zooms out), so
// innerWidth is not the screen width. Measure against the device width we emulate.
const MEASURE = (vw) => `(() => {
  const vw = ${vw};
  const doc = document.documentElement.scrollWidth;
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.right <= vw + 0.5) continue;
    // report only the innermost offenders: skip if a child also sticks out
    if ([...el.children].some((c) => c.getBoundingClientRect().right > vw + 0.5)) continue;
    // Fine inside a container that scrolls sideways on its own (e.g. a wide table, the tab row).
    // Content cut off by overflow: hidden still counts: the user cannot reach it.
    let scrolls = false;
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if ((o === "auto" || o === "scroll") && p.getBoundingClientRect().right <= vw + 0.5) {
        scrolls = true;
        break;
      }
    }
    if (scrolls) continue;
    const st = getComputedStyle(el);
    if (st.visibility === "hidden" || st.position === "fixed" || el.closest(".maplibregl-map, .sr-only")) continue;
    const cls = typeof el.className === "string" ? el.className.split(" ")[0] : "";
    out.push(el.tagName.toLowerCase() + (cls ? "." + cls : "") + " right=" + Math.round(r.right));
    if (out.length >= 8) break;
  }
  return { vw, doc, out, at: location.hash.slice(0, 40) + (document.querySelector(".tour-dialog") ? " [tour]" : "") + (document.querySelector(".sim3d-select") ? " [sim3d]" : "") };
})()`;

await send("Runtime.enable");
await send("Page.enable");
let failures = 0;
for (const width of WIDTHS) {
  await send("Emulation.setDeviceMetricsOverride", { width, height: 800, deviceScaleFactor: 1, mobile: true });
  for (const route of ROUTES) {
    await send("Page.navigate", { url: "about:blank" });
    await sleep(100);
    await send("Page.navigate", { url: new URL(base).origin + new URL(base).pathname + route });
    await sleep(300);
    await evaluate(SETTLE);
    const { vw, doc, out, at } = await evaluate(MEASURE(width));
    const ok = doc <= vw && out.length === 0;
    if (!ok) failures++;
    console.log(`${ok ? "PASS" : "FAIL"} ${width}px ${route} (document ${doc} px, viewport ${vw} px) ${at}`);
    for (const o of ok ? [] : out) console.log(`    ${o}`);
  }
}
ws.close();
chrome.kill();
console.log(failures ? `${failures} route(s) scroll sideways` : "no horizontal page scroll on any route");
process.exit(failures ? 1 : 0);
