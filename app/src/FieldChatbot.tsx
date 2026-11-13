import { useEffect, useRef, useState } from "react";
import { type CallResult, type HistoryItem, type MessageKind, buildMessages, callAssistant } from "./chatbotClient";
import {
  type ChatAnswer,
  type ChatContextSnapshot,
  answerQuestion,
  getActiveFieldPack,
  resolveFieldLabel,
  shouldAnswerLocally,
  subscribeActiveFieldPack,
  violatesGuardrails,
} from "./chatbotContext";
import { t } from "./strings";
import type { FieldPack, RegionIndex } from "./types";

interface ChatMessage extends HistoryItem {
  id: string;
  kind: MessageKind;
  sourceLabel?: string;
  followUps?: string[];
  note?: string;
}

interface OwnKeyConfig {
  enabled: boolean;
  endpoint: string;
  model: string;
  apiKey: string;
}

// Opt-in only. The default path is the key-less proxy below.
const OWN_KEY_STORAGE = "fieldwitness_chatbot_own_key_v2";
const PROXY_URL = ((import.meta.env.VITE_CHATBOT_PROXY_URL as string | undefined) ?? "").trim();
const EMPTY_OWN_KEY: OwnKeyConfig = { enabled: false, endpoint: "", model: "", apiKey: "" };

function loadOwnKey(): OwnKeyConfig {
  try {
    const raw = localStorage.getItem(OWN_KEY_STORAGE);
    if (raw) return { ...EMPTY_OWN_KEY, ...(JSON.parse(raw) as Partial<OwnKeyConfig>) };
  } catch {
    // storage blocked: stay with the defaults
  }
  return EMPTY_OWN_KEY;
}

let nextId = 0;
const newId = (p: string) => `${p}-${Date.now()}-${nextId++}`;

/** Friendly one-line note for a failed call; never shows raw HTTP bodies. */
export function failureNote(r: Exclude<CallResult, { ok: true }>): string {
  if (r.reason === "offline") return t("chat.note.offline");
  if (r.reason === "aborted") return t("chat.note.stopped");
  if (r.reason === "rate_limited") return t("chat.note.busy", { s: r.retryAfterS ?? 60 });
  return t("chat.note.unavailable");
}

export function FieldChatbot({
  page,
  regionId,
  fieldId,
  index,
}: {
  page: string;
  regionId: string;
  fieldId?: string;
  index: RegionIndex | null;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [activePack, setActivePack] = useState<FieldPack | null>(() => getActiveFieldPack());
  const [ownKey, setOwnKey] = useState<OwnKeyConfig>(() => loadOwnKey());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: "welcome",
      role: "assistant",
      kind: "note",
      text: t("chat.welcome"),
      sourceLabel: t("chat.title"),
      followUps: ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
    },
  ]);

  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const launcherRef = useRef<HTMLButtonElement | null>(null);
  const stopRef = useRef<AbortController | null>(null);
  const wasOpen = useRef(false);

  useEffect(() => subscribeActiveFieldPack(setActivePack), []);

  useEffect(() => {
    if (!fieldId) setActivePack(null);
  }, [fieldId]);

  useEffect(() => {
    if (isOpen && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isOpen, isLoading]);

  // Focus: input on open, launcher on close.
  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
    else if (wasOpen.current) launcherRef.current?.focus();
    wasOpen.current = isOpen;
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  useEffect(() => () => stopRef.current?.abort(), []);

  const fieldLabel = resolveFieldLabel(activePack, index);
  const ctx: ChatContextSnapshot = {
    page: fieldId ? "field" : page || "map",
    regionId,
    fieldId,
    fieldNumberLabel: fieldLabel,
    fieldPack: activePack,
  };

  const contextSummary = activePack
    ? `Field ${fieldLabel ?? activePack.field.field_id.slice(0, 8)} (${activePack.field.area_ha.toFixed(1)} ha)`
    : `${ctx.page.toUpperCase()} · ${regionId}`;

  const useOwnKey = ownKey.enabled && ownKey.endpoint.trim() !== "" && ownKey.apiKey.trim() !== "";
  const llmEndpoint = useOwnKey ? ownKey.endpoint.trim() : PROXY_URL;

  const saveOwnKey = (next: OwnKeyConfig) => {
    setOwnKey(next);
    try {
      if (next.enabled || next.apiKey) localStorage.setItem(OWN_KEY_STORAGE, JSON.stringify(next));
      else localStorage.removeItem(OWN_KEY_STORAGE);
    } catch {
      // storage blocked: keep it in memory only
    }
  };

  const grounded = (ans: ChatAnswer, note?: string): ChatMessage => ({
    id: newId("a"),
    role: "assistant",
    kind: "grounded",
    text: ans.text,
    sourceLabel: ans.sourceLabel,
    followUps: ans.followUps,
    note,
  });

  const handleSend = async (rawText?: string) => {
    const query = (rawText ?? input).trim();
    if (!query || isLoading) return;
    const history = messages;
    setMessages((prev) => [...prev, { id: newId("u"), role: "user", kind: "llm", text: query }]);
    if (!rawText) setInput("");

    if (!llmEndpoint || shouldAnswerLocally(query, ctx)) {
      setMessages((prev) => [...prev, grounded(answerQuestion(query, ctx))]);
      return;
    }

    const stop = new AbortController();
    stopRef.current = stop;
    setIsLoading(true);
    const result = await callAssistant({
      endpoint: llmEndpoint,
      messages: buildMessages(query, history, ctx),
      apiKey: useOwnKey ? ownKey.apiKey.trim() : undefined,
      model: useOwnKey ? ownKey.model.trim() : undefined,
      signal: stop.signal,
    });
    stopRef.current = null;
    setIsLoading(false);

    let reply: ChatMessage;
    if (result.ok && !violatesGuardrails(result.text)) {
      reply = { id: newId("a"), role: "assistant", kind: "llm", text: result.text, sourceLabel: t("chat.label.llm") };
    } else if (result.ok) {
      reply = grounded(answerQuestion(query, ctx), t("chat.note.guardrail"));
    } else if (result.reason === "aborted") {
      reply = { id: newId("n"), role: "assistant", kind: "note", text: t("chat.note.stopped") };
    } else {
      reply = grounded(answerQuestion(query, ctx), failureNote(result));
    }
    setMessages((prev) => [...prev, reply]);
  };

  return (
    <div className="chatbot-root">
      {isOpen && (
        <section className="chatbot-drawer" role="dialog" aria-label={t("chat.title")}>
          <header className="chatbot-header">
            <div className="chatbot-title-wrap">
              <strong className="chatbot-title">{t("chat.title")}</strong>
              <span className="chatbot-ctx-pill">{contextSummary}</span>
            </div>
            <button
              type="button"
              className="chatbot-icon-btn"
              onClick={() => setIsOpen(false)}
              aria-label={t("chat.close")}
            >
              ✕
            </button>
          </header>

          <div className="chatbot-messages" ref={listRef} aria-live="polite" aria-relevant="additions">
            {messages.map((m) => (
              <div key={m.id} className={`chatbot-msg chatbot-msg--${m.role}`}>
                <div className={`chatbot-bubble${m.kind === "llm" && m.role === "assistant" ? " chatbot-bubble--llm" : ""}`}>
                  <p className="chatbot-text">{m.text}</p>
                  {m.note && <p className="chatbot-note">{m.note}</p>}
                  {m.sourceLabel && <span className="chatbot-source">{m.sourceLabel}</span>}
                </div>
                {m.role === "assistant" && m.followUps && m.followUps.length > 0 && (
                  <div className="chatbot-chips">
                    {m.followUps.map((chip) => (
                      <button key={chip} type="button" className="chatbot-chip" onClick={() => handleSend(chip)}>
                        {chip}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="chatbot-msg chatbot-msg--assistant">
                <div className="chatbot-bubble">
                  <p className="chatbot-text">{t("chat.thinking")}</p>
                </div>
              </div>
            )}
          </div>

          <form
            className="chatbot-form"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              ref={inputRef}
              type="text"
              className="chatbot-input"
              maxLength={2000}
              placeholder={activePack ? t("chat.input.field", { n: fieldLabel ?? "" }) : t("chat.input.general")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              aria-label={t("chat.input.label")}
            />
            {isLoading ? (
              <button type="button" className="chatbot-send-btn" onClick={() => stopRef.current?.abort()}>
                {t("chat.stop")}
              </button>
            ) : (
              <button type="submit" className="chatbot-send-btn" disabled={!input.trim()}>
                {t("chat.send")}
              </button>
            )}
          </form>

          {llmEndpoint && <p className="chatbot-privacy">{t("chat.privacy")}</p>}

          <details className="chatbot-advanced">
            <summary>{t("chat.advanced.summary")}</summary>
            <p className="chatbot-settings-note">{t("chat.advanced.warning")}</p>
            <label className="chatbot-check">
              <input
                type="checkbox"
                checked={ownKey.enabled}
                onChange={(e) => saveOwnKey({ ...ownKey, enabled: e.target.checked })}
              />
              {t("chat.advanced.enable")}
            </label>
            {ownKey.enabled && (
              <>
                <input
                  type="url"
                  className="chatbot-setting-input"
                  aria-label={t("chat.advanced.endpoint")}
                  placeholder={t("chat.advanced.endpoint")}
                  value={ownKey.endpoint}
                  onChange={(e) => saveOwnKey({ ...ownKey, endpoint: e.target.value })}
                />
                <input
                  type="text"
                  className="chatbot-setting-input"
                  aria-label={t("chat.advanced.model")}
                  placeholder={t("chat.advanced.model")}
                  value={ownKey.model}
                  onChange={(e) => saveOwnKey({ ...ownKey, model: e.target.value })}
                />
                <input
                  type="password"
                  autoComplete="off"
                  className="chatbot-setting-input"
                  aria-label={t("chat.advanced.key")}
                  placeholder={t("chat.advanced.key")}
                  value={ownKey.apiKey}
                  onChange={(e) => saveOwnKey({ ...ownKey, apiKey: e.target.value })}
                />
                <button type="button" className="chatbot-icon-btn" onClick={() => saveOwnKey(EMPTY_OWN_KEY)}>
                  {t("chat.advanced.clear")}
                </button>
              </>
            )}
          </details>
        </section>
      )}

      <button
        ref={launcherRef}
        type="button"
        className="chatbot-fab"
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
      >
        {isOpen ? t("chat.launcher.close") : t("chat.launcher")}
      </button>
    </div>
  );
}
