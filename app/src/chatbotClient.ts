/**
 * Network side of the assistant: build the message list and call the chat proxy (or, only when
 * the user opts in under "Advanced", their own OpenAI-compatible endpoint with their own key).
 * The default proxy (VITE_CHATBOT_PROXY_URL, workers/chat-proxy) holds the key server-side; no
 * key is ever shipped in the bundle.
 */
import { type ChatContextSnapshot, buildSystemPrompt } from "./chatbotContext";

export type ChatRole = "user" | "assistant";

/** "llm" = a generated reply; "grounded" = local KB or field-pack answer; "note" = UI notice. */
export type MessageKind = "llm" | "grounded" | "note";

export interface HistoryItem {
  role: ChatRole;
  text: string;
  kind?: MessageKind;
}

export interface WireMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export const MAX_HISTORY = 6;
export const MAX_TOTAL_CHARS = 11_000; // the proxy rejects > 12,000
export const TIMEOUT_MS = 20_000;

const FALLBACK_TAG_RE = /\n*\[LLM fallback reason:[^\]]*\]/g;

/**
 * Prior turns sent to the LLM: only the user's own questions and earlier LLM replies.
 * Grounded answers and notices are dropped, and any old "[LLM fallback reason: ...]" text is
 * stripped. An assistant turn without a preceding user turn is dropped too.
 */
export function historyForLlm(items: HistoryItem[]): WireMessage[] {
  const kept: WireMessage[] = [];
  for (const m of items) {
    if (m.role === "assistant" && m.kind !== "llm") continue;
    const content = m.text.replace(FALLBACK_TAG_RE, "").trim();
    if (!content) continue;
    kept.push({ role: m.role, content });
  }
  const tail = kept.slice(-MAX_HISTORY);
  while (tail.length > 0 && tail[0].role === "assistant") tail.shift();
  return tail;
}

export function buildMessages(query: string, history: HistoryItem[], ctx: ChatContextSnapshot): WireMessage[] {
  const system: WireMessage = { role: "system", content: buildSystemPrompt(ctx, query) };
  const user: WireMessage = { role: "user", content: query.slice(0, 2_000) };
  const prior = historyForLlm(history);
  const size = (ms: WireMessage[]) => ms.reduce((n, m) => n + m.content.length, 0);
  while (prior.length > 0 && size([system, ...prior, user]) > MAX_TOTAL_CHARS) prior.shift();
  if (system.content.length + user.content.length > MAX_TOTAL_CHARS) {
    system.content = system.content.slice(0, MAX_TOTAL_CHARS - user.content.length);
  }
  return [system, ...prior, user];
}

export type CallResult =
  | { ok: true; text: string; model: string | null }
  | { ok: false; reason: "offline" | "timeout" | "aborted" | "rate_limited" | "server" | "network" | "bad_reply" | "bad_request"; retryAfterS?: number };

export interface CallOptions {
  endpoint: string;
  messages: WireMessage[];
  /** Only for the opt-in "use my own key" mode; never set for the default proxy. */
  apiKey?: string;
  model?: string;
  timeoutMs?: number;
  /** Caller's Stop button. */
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  isOnline?: () => boolean;
}

function defaultOnline(): boolean {
  return typeof navigator === "undefined" || (navigator as { onLine?: boolean }).onLine !== false;
}

export async function callAssistant(opts: CallOptions): Promise<CallResult> {
  const isOnline = opts.isOnline ?? defaultOnline;
  if (!isOnline()) return { ok: false, reason: "offline" };
  if (opts.signal?.aborted) return { ok: false, reason: "aborted" };

  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctrl.abort();
  }, opts.timeoutMs ?? TIMEOUT_MS);
  const onStop = () => ctrl.abort();
  opts.signal?.addEventListener("abort", onStop);

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const body: Record<string, unknown> = { messages: opts.messages };
  if (opts.apiKey) {
    headers.Authorization = `Bearer ${opts.apiKey}`;
    body.model = opts.model;
    body.temperature = 0.2;
    body.max_tokens = 400;
  }

  try {
    const res = await (opts.fetchImpl ?? fetch)(opts.endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: ctrl.signal,
      cache: "no-store",
      credentials: "omit",
    });
    if (res.status === 429) {
      const ra = Number.parseInt(res.headers.get("Retry-After") ?? "", 10);
      return { ok: false, reason: "rate_limited", retryAfterS: Number.isFinite(ra) ? ra : undefined };
    }
    if (res.status >= 500) return { ok: false, reason: "server" };
    if (!res.ok) return { ok: false, reason: "bad_request" };
    const data = (await res.json().catch(() => null)) as {
      choices?: { message?: { content?: unknown } }[];
      model?: unknown;
    } | null;
    const text = data?.choices?.[0]?.message?.content;
    if (typeof text !== "string" || !text.trim()) return { ok: false, reason: "bad_reply" };
    return { ok: true, text: text.trim(), model: typeof data?.model === "string" ? data.model : (opts.model ?? null) };
  } catch {
    if (timedOut) return { ok: false, reason: "timeout" };
    if (opts.signal?.aborted) return { ok: false, reason: "aborted" };
    return { ok: false, reason: isOnline() ? "network" : "offline" };
  } finally {
    clearTimeout(timer);
    opts.signal?.removeEventListener("abort", onStop);
  }
}
