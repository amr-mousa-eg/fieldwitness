// Offline acceptance check (T9.1): visit once online, wait for the service worker and caches,
// go offline, reload, and check the app shell renders. Usage: node offline.mjs <url> <out.png>
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, out] = process.argv.slice(2);
const port = 9334;
const chrome = spawn(process.env.CHROME ?? "C:/Program Files/Google/Chrome/Application/chrome.exe", [
  "--headless=new",
  "--enable-unsafe-swiftshader",
  "--use-angle=swiftshader",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "fw-off-"))}`,
  "--window-size=1280,800",
  "about:blank",
]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 50 && !wsUrl; i++) {
  await sleep(200);
  try {
    wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page")
      ?.webSocketDebuggerUrl;
  } catch {}
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
const errors = [];
ws.addEventListener("message", (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) return pending.get(m.id)(m), pending.delete(m.id);
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.text);
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error")
    errors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
});
const send = (method, params = {}) =>
  new Promise((r) => (pending.set(++id, r), ws.send(JSON.stringify({ id, method, params }))));
const evaluate = async (expr) =>
  (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result
    ?.value;
const waitFor = async (expr, ms = 20000) => {
  for (let t = 0; t < ms; t += 250) {
    if (await evaluate(expr)) return true;
    await sleep(250);
  }
  return false;
};

await send("Runtime.enable");
await send("Network.enable");
await send("Page.navigate", { url });
const controlled = await waitFor("!!navigator.serviceWorker.controller");
await sleep(1500); // let the shell caching finish
const cached = await evaluate(
  "caches.open('fw-app-v1').then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname))",
);
console.log("controlled:", controlled);
console.log("app cache:", JSON.stringify(cached));

await send("Network.emulateNetworkConditions", {
  offline: true,
  latency: 0,
  downloadThroughput: -1,
  uploadThroughput: -1,
});
errors.length = 0;
await send("Page.reload", { ignoreCache: false });
const shell = await waitFor("!!document.querySelector('.app-header h1')", 10000);
await sleep(500);
const shot = await send("Page.captureScreenshot", { format: "png" });
writeFileSync(out, Buffer.from(shot.result.data, "base64"));
console.log("offline reload renders the app shell:", shell);
console.log("offline page text:", JSON.stringify((await evaluate("document.body.innerText")).slice(0, 300)));
console.log("errors while offline:", errors.length ? errors : "none");
ws.close();
chrome.kill();
process.exit(shell ? 0 : 1);
