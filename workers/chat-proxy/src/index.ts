/**
 * FieldWitness chat proxy — Cloudflare Worker (free plan).
 *
 * Keeps the LLM API key on the server. The static site sends only `{messages}`; this Worker fixes
 * the model, temperature and max_tokens, validates the request, applies a per-IP rate limit and a
 * daily cap, and returns an OpenAI-style `{choices:[{message:{content}}]}` body.
 * Upstream error bodies and headers are never passed to the client.
 *
 * Upstream: any OpenAI-compatible chat-completions API, chosen by env vars (docs/api_notes.md):
 *   Google Gemini  LLM_BASE_URL = https://generativelanguage.googleapis.com/v1beta/openai
 *   Groq           LLM_BASE_URL = https://api.groq.com/openai/v1
 * The Worker always POSTs to `${LLM_BASE_URL}/chat/completions` with `Authorization: Bearer <key>`.
 *
 * Only erasable TypeScript syntax is used so `node --test` can run the tests without a build step.
 */

export interface RateLimitBinding {
  limit(opts: { key: string }): Promise<{ success: boolean }>;
}

export interface KvBinding {
  get(key: string): Promise<string | null>;
  put(key: string, value: string, opts?: { expirationTtl?: number }): Promise<void>;
}

export interface Env {
  LLM_API_KEY?: string; // secret: `npx wrangler secret put LLM_API_KEY`
  LLM_BASE_URL?: string;
  LLM_MODEL?: string;
  LLM_PROVIDER?: string; // label only, e.g. "google" or "groq"
  LLM_REASONING_EFFORT?: string; // optional, sent only when set (Gemini thinking models)
  MAX_TOKENS?: string;
  DAILY_CAP?: string;
  ALLOWED_ORIGIN?: string;
  RATE_LIMITER?: RateLimitBinding; // [[ratelimits]] binding, per IP
  USAGE?: KvBinding; // KV namespace for the daily cap
}

export const LIMITS = {
  maxMessages: 8,
  maxTotalChars: 12_000,
  maxBodyBytes: 32_000,
  temperature: 0.2,
  defaultMaxTokens: 400,
  defaultDailyCap: 500,
  upstreamTimeoutMs: 25_000,
} as const;

const DEFAULT_ORIGIN = "https://amr-mousa-eg.github.io";
const ROLES = new Set(["system", "user", "assistant"]);
const LOCAL_ORIGIN = /^http:\/\/(localhost|127\.0\.0\.1)(:\d{1,5})?$/;

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export function isAllowedOrigin(origin: string | null, allowed: string = DEFAULT_ORIGIN): boolean {
  if (!origin) return false;
  return origin === allowed || LOCAL_ORIGIN.test(origin);
}

export function corsHeaders(origin: string | null, allowed: string = DEFAULT_ORIGIN): Record<string, string> {
  const h: Record<string, string> = { Vary: "Origin" };
  if (origin && isAllowedOrigin(origin, allowed)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "POST, OPTIONS";
    h["Access-Control-Allow-Headers"] = "Content-Type";
    h["Access-Control-Max-Age"] = "86400";
  }
  return h;
}

export type Validation = { ok: true; messages: ChatMessage[] } | { ok: false; code: string; message: string };

/** Accepts only `{messages}`; every other field (model, temperature, endpoint, ...) is ignored. */
export function validateBody(body: unknown): Validation {
  const bad = (message: string): Validation => ({ ok: false, code: "invalid_messages", message });
  if (typeof body !== "object" || body === null || Array.isArray(body)) return bad("Body must be a JSON object.");
  const raw = (body as { messages?: unknown }).messages;
  if (!Array.isArray(raw) || raw.length === 0) return bad("`messages` must be a non-empty array.");
  if (raw.length > LIMITS.maxMessages) return bad(`At most ${LIMITS.maxMessages} messages are allowed.`);
  const messages: ChatMessage[] = [];
  let total = 0;
  for (const m of raw) {
    if (typeof m !== "object" || m === null) return bad("Each message must be an object.");
    const { role, content } = m as { role?: unknown; content?: unknown };
    if (typeof role !== "string" || !ROLES.has(role)) return bad("Roles must be system, user or assistant.");
    if (typeof content !== "string" || !content.trim()) return bad("Each message needs non-empty text content.");
    total += content.length;
    messages.push({ role: role as ChatMessage["role"], content });
  }
  if (total > LIMITS.maxTotalChars) return bad(`Messages exceed ${LIMITS.maxTotalChars} characters in total.`);
  if (messages[messages.length - 1].role !== "user") return bad("The last message must come from the user.");
  return { ok: true, messages };
}

export function upstreamRequest(env: Env, messages: ChatMessage[]): { url: string; init: RequestInit } {
  const base = (env.LLM_BASE_URL ?? "").replace(/\/+$/, "");
  const maxTokens = Number.parseInt(env.MAX_TOKENS ?? "", 10);
  const payload: Record<string, unknown> = {
    model: env.LLM_MODEL,
    messages,
    temperature: LIMITS.temperature,
    max_tokens: Number.isFinite(maxTokens) && maxTokens > 0 ? maxTokens : LIMITS.defaultMaxTokens,
  };
  if (env.LLM_REASONING_EFFORT) payload.reasoning_effort = env.LLM_REASONING_EFFORT;
  return {
    url: `${base}/chat/completions`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${env.LLM_API_KEY}` },
      body: JSON.stringify(payload),
    },
  };
}

function secondsToUtcMidnight(now: Date): number {
  const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  return Math.max(1, Math.ceil((next - now.getTime()) / 1000));
}

/**
 * Approximate global daily cap kept in KV (free plan: 1,000 writes/day, 1 write/s per key).
 * Read-modify-write is not atomic, so bursts can overshoot slightly; that is accepted.
 * Returns null when allowed, or the seconds until the cap resets.
 */
export async function checkDailyCap(env: Env, now: Date): Promise<number | null> {
  if (!env.USAGE) return null;
  const cap = Number.parseInt(env.DAILY_CAP ?? "", 10);
  const limit = Number.isFinite(cap) && cap > 0 ? cap : LIMITS.defaultDailyCap;
  const key = `count:${now.toISOString().slice(0, 10)}`;
  try {
    const used = Number.parseInt((await env.USAGE.get(key)) ?? "0", 10) || 0;
    if (used >= limit) return secondsToUtcMidnight(now);
    await env.USAGE.put(key, String(used + 1), { expirationTtl: 172_800 });
  } catch {
    // KV hiccup (e.g. >1 write/s on one key): do not block the user, the per-IP limit still applies.
  }
  return null;
}

function json(status: number, body: unknown, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers, "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function fail(status: number, code: string, message: string, headers: Record<string, string>, retryAfter?: number) {
  const h = retryAfter ? { ...headers, "Retry-After": String(retryAfter) } : headers;
  return json(status, { error: { code, message, ...(retryAfter ? { retry_after_s: retryAfter } : {}) } }, h);
}

export async function handle(request: Request, env: Env, fetchImpl: typeof fetch = fetch): Promise<Response> {
  const allowed = env.ALLOWED_ORIGIN || DEFAULT_ORIGIN;
  const origin = request.headers.get("Origin");
  const cors = corsHeaders(origin, allowed);

  if (!isAllowedOrigin(origin, allowed)) return fail(403, "origin_not_allowed", "Origin not allowed.", cors);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (request.method !== "POST") return fail(405, "method_not_allowed", "Use POST.", cors);
  if (!(request.headers.get("Content-Type") ?? "").includes("application/json")) {
    return fail(415, "unsupported_media_type", "Send application/json.", cors);
  }

  const text = await request.text();
  if (text.length > LIMITS.maxBodyBytes) return fail(413, "payload_too_large", "Request too large.", cors);
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    return fail(400, "invalid_json", "Body is not valid JSON.", cors);
  }
  const v = validateBody(body);
  if (!v.ok) return fail(400, v.code, v.message, cors);

  if (!env.LLM_API_KEY || !env.LLM_BASE_URL || !env.LLM_MODEL) {
    return fail(503, "not_configured", "Assistant is not configured.", cors);
  }

  if (env.RATE_LIMITER) {
    const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";
    const { success } = await env.RATE_LIMITER.limit({ key: ip });
    if (!success) return fail(429, "rate_limited", "Too many questions. Try again in a minute.", cors, 60);
  }
  const capWait = await checkDailyCap(env, new Date());
  if (capWait !== null) return fail(429, "daily_cap", "Daily question limit reached. Try again tomorrow.", cors, capWait);

  const { url, init } = upstreamRequest(env, v.messages);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), LIMITS.upstreamTimeoutMs);
  let upstream: Response;
  try {
    upstream = await fetchImpl(url, { ...init, signal: ctrl.signal });
  } catch {
    clearTimeout(timer);
    return ctrl.signal.aborted
      ? fail(504, "upstream_timeout", "The language model took too long.", cors)
      : fail(502, "upstream_unreachable", "The language model could not be reached.", cors);
  }
  clearTimeout(timer);

  if (upstream.status === 429) {
    return fail(429, "upstream_rate_limited", "The free model quota is busy. Try again in a minute.", cors, 60);
  }
  if (!upstream.ok) return fail(502, "upstream_error", "The language model returned an error.", cors);

  let content: unknown;
  try {
    const data = (await upstream.json()) as { choices?: { message?: { content?: unknown } }[] };
    content = data?.choices?.[0]?.message?.content;
  } catch {
    content = undefined;
  }
  if (typeof content !== "string" || !content.trim()) {
    return fail(502, "empty_reply", "The language model returned no text.", cors);
  }
  return json(
    200,
    {
      choices: [{ index: 0, message: { role: "assistant", content: content.trim() } }],
      model: env.LLM_MODEL,
      provider: env.LLM_PROVIDER ?? null,
    },
    cors,
  );
}

export default {
  fetch(request: Request, env: Env): Promise<Response> {
    return handle(request, env);
  },
};
