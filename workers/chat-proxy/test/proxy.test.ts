// Run: node --test workers/chat-proxy/test/  (Node >= 23.6 strips the types; no dependencies.)
import assert from "node:assert/strict";
import { test } from "node:test";
import { type Env, LIMITS, checkDailyCap, corsHeaders, handle, isAllowedOrigin, validateBody } from "../src/index.ts";

const SITE = "https://amr-mousa-eg.github.io";
const ENV: Env = {
  LLM_API_KEY: "test-key-not-real",
  LLM_BASE_URL: "https://upstream.invalid/v1/",
  LLM_MODEL: "test-model",
};
const ok = (content: string) =>
  new Response(JSON.stringify({ choices: [{ message: { content } }] }), { status: 200 });

function req(body: unknown, origin: string | null = SITE, method = "POST"): Request {
  const headers: Record<string, string> = { "Content-Type": "application/json", "CF-Connecting-IP": "1.2.3.4" };
  if (origin) headers.Origin = origin;
  return new Request("https://proxy.invalid/", {
    method,
    headers,
    body: method === "POST" ? JSON.stringify(body) : undefined,
  });
}
const userMsg = { messages: [{ role: "user", content: "What is FieldWitness?" }] };

test("CORS allowlist: site and localhost only", () => {
  assert.ok(isAllowedOrigin(SITE));
  assert.ok(isAllowedOrigin("http://localhost:5173"));
  assert.ok(isAllowedOrigin("http://127.0.0.1:4173"));
  assert.ok(isAllowedOrigin("http://localhost"));
  for (const o of [null, "", "https://evil.example", "https://amr-mousa-eg.github.io.evil.example", "https://localhost:5173", "http://localhost.evil.example"]) {
    assert.equal(isAllowedOrigin(o), false, String(o));
  }
  assert.equal(corsHeaders("https://evil.example")["Access-Control-Allow-Origin"], undefined);
  assert.equal(corsHeaders(SITE)["Access-Control-Allow-Origin"], SITE);
});

test("OPTIONS preflight from allowed origin returns 204 with CORS", async () => {
  const res = await handle(req(null, SITE, "OPTIONS"), ENV);
  assert.equal(res.status, 204);
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), SITE);
  assert.match(res.headers.get("Access-Control-Allow-Methods") ?? "", /POST/);
});

test("disallowed or missing origin is rejected with 403 and no CORS header", async () => {
  for (const o of ["https://evil.example", null]) {
    const res = await handle(req(userMsg, o), ENV, async () => ok("x"));
    assert.equal(res.status, 403);
    assert.equal(res.headers.get("Access-Control-Allow-Origin"), null);
  }
});

test("validation: limits, roles, shape", () => {
  assert.equal(validateBody(userMsg).ok, true);
  const many = { messages: Array.from({ length: LIMITS.maxMessages + 1 }, () => ({ role: "user", content: "hi" })) };
  assert.equal(validateBody(many).ok, false);
  assert.equal(validateBody({ messages: [{ role: "tool", content: "x" }] }).ok, false);
  assert.equal(validateBody({ messages: [{ role: "user", content: "" }] }).ok, false);
  assert.equal(validateBody({ messages: [{ role: "user", content: 5 }] }).ok, false);
  assert.equal(validateBody({ messages: [{ role: "user", content: "x".repeat(LIMITS.maxTotalChars + 1) }] }).ok, false);
  assert.equal(validateBody({ messages: [{ role: "assistant", content: "x" }] }).ok, false);
  assert.equal(validateBody([]).ok, false);
  assert.equal(validateBody({}).ok, false);
});

test("client model/temperature/endpoint are ignored; server values are sent", async () => {
  let sentUrl = "";
  let sent: Record<string, unknown> = {};
  const fetchSpy = (async (url: string, init: RequestInit) => {
    sentUrl = url;
    sent = JSON.parse(String(init.body));
    return ok("Hello");
  }) as unknown as typeof fetch;
  const res = await handle(
    req({ ...userMsg, model: "gpt-expensive", temperature: 2, endpoint: "https://evil.example", max_tokens: 9999 }),
    ENV,
    fetchSpy,
  );
  assert.equal(res.status, 200);
  assert.equal(sentUrl, "https://upstream.invalid/v1/chat/completions");
  assert.equal(sent.model, "test-model");
  assert.equal(sent.temperature, 0.2);
  assert.equal(sent.max_tokens, LIMITS.defaultMaxTokens);
  const body = (await res.json()) as { choices: { message: { content: string } }[] };
  assert.equal(body.choices[0].message.content, "Hello");
});

test("bad JSON, wrong method, wrong content type, bad body", async () => {
  const bad = new Request("https://proxy.invalid/", {
    method: "POST",
    headers: { Origin: SITE, "Content-Type": "application/json" },
    body: "{not json",
  });
  assert.equal((await handle(bad, ENV)).status, 400);
  assert.equal((await handle(req(null, SITE, "GET"), ENV)).status, 405);
  const text = new Request("https://proxy.invalid/", { method: "POST", headers: { Origin: SITE }, body: "hi" });
  assert.equal((await handle(text, ENV)).status, 415);
  const res = await handle(req({ messages: [] }), ENV);
  assert.equal(res.status, 400);
  const err = (await res.json()) as { error: { code: string } };
  assert.equal(err.error.code, "invalid_messages");
});

test("upstream errors are not echoed", async () => {
  const secretish = "UPSTREAM-INTERNAL-DETAIL";
  const res = await handle(req(userMsg), ENV, async () => new Response(secretish, { status: 500, headers: { "X-Upstream": "1" } }));
  assert.equal(res.status, 502);
  const text = await res.text();
  assert.ok(!text.includes(secretish));
  assert.equal(res.headers.get("X-Upstream"), null);
  const r429 = await handle(req(userMsg), ENV, async () => new Response(secretish, { status: 429 }));
  assert.equal(r429.status, 429);
  assert.ok(r429.headers.get("Retry-After"));
  assert.ok(!(await r429.text()).includes(secretish));
  const net = await handle(req(userMsg), ENV, (async () => {
    throw new Error(secretish);
  }) as unknown as typeof fetch);
  assert.equal(net.status, 502);
  assert.ok(!(await net.text()).includes(secretish));
  const empty = await handle(req(userMsg), ENV, async () => ok("   "));
  assert.equal(empty.status, 502);
});

test("missing configuration returns 503 not_configured", async () => {
  const res = await handle(req(userMsg), { LLM_BASE_URL: "x", LLM_MODEL: "y" });
  assert.equal(res.status, 503);
});

test("per-IP rate limit returns 429 with retry hint", async () => {
  const env: Env = { ...ENV, RATE_LIMITER: { limit: async () => ({ success: false }) } };
  const res = await handle(req(userMsg), env, async () => ok("x"));
  assert.equal(res.status, 429);
  assert.equal(res.headers.get("Retry-After"), "60");
  const body = (await res.json()) as { error: { code: string; retry_after_s: number } };
  assert.equal(body.error.code, "rate_limited");
});

test("daily cap counts in KV and blocks at the cap", async () => {
  const store = new Map<string, string>();
  const kv = { get: async (k: string) => store.get(k) ?? null, put: async (k: string, v: string) => void store.set(k, v) };
  const env: Env = { ...ENV, DAILY_CAP: "2", USAGE: kv };
  const now = new Date("2026-11-13T12:00:00Z");
  assert.equal(await checkDailyCap(env, now), null);
  assert.equal(await checkDailyCap(env, now), null);
  assert.equal(await checkDailyCap(env, now), 12 * 3600);
  assert.equal(store.get("count:2026-11-13"), "2");
});
