// Dev helper (needs a local Chrome; set CHROME=<path> if elsewhere). Minimal CDP driver: open URL, wait for a selector, print console
// errors, save a screenshot. Usage: node shot.mjs <url> <selector> <out.png> [width] [height] [dark|light] [js]
// [js] is an optional expression run in the page once the selector is ready (e.g. a click).
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, selector, out, w = "1280", h = "800", scheme = "light", action] = process.argv.slice(2);
const CHROME = process.env.CHROME ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";
const port = 9333;
const chrome = spawn(CHROME, [
  "--headless=new",
  "--enable-unsafe-swiftshader",
  "--use-angle=swiftshader",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "fw-cdp-"))}`,
  `--window-size=${w},${h}`,
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
const problems = [];
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  } else if (msg.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(msg.params.type)) {
    problems.push(`console.${msg.params.type}: ${msg.params.args.map((a) => a.value ?? a.description).join(" ")}`);
  } else if (msg.method === "Runtime.exceptionThrown") {
    problems.push(`exception: ${msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text}`);
  }
});
const send = (method, params = {}) =>
  new Promise((r) => {
    pending.set(++id, r);
    ws.send(JSON.stringify({ id, method, params }));
  });

await send("Runtime.enable");
await send("Page.enable");
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: scheme }] });
// Headless Chrome windows have a minimum width (~500 px); emulate the exact viewport instead.
await send("Emulation.setDeviceMetricsOverride", {
  width: Number(w),
  height: Number(h),
  deviceScaleFactor: 1,
  mobile: Number(w) < 600,
});
await send("Page.navigate", { url });
let found = false;
for (let i = 0; i < 100 && !found; i++) {
  await sleep(200);
  const r = await send("Runtime.evaluate", { expression: `!!document.querySelector(${JSON.stringify(selector)})` });
  found = r.result?.result?.value === true;
}
if (found && action) await send("Runtime.evaluate", { expression: action });
await sleep(300);
const shot = await send("Page.captureScreenshot", { format: "png" });
writeFileSync(out, Buffer.from(shot.result.data, "base64"));
console.log(found ? `ready: ${selector}` : `TIMEOUT waiting for ${selector}`);
console.log(problems.length ? problems.join("\n") : "no console errors or warnings");
ws.close();
chrome.kill();
process.exit(found ? 0 : 1);
