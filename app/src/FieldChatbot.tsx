import { Fragment, type ReactNode, useEffect, useRef, useState } from "react";
import {
  type ChatContextSnapshot,
  type LiveChatStoreState,
  answerQuestion,
  buildSystemPrompt,
  getLiveChatState,
  resolveFieldLabel,
  subscribeLiveChatState,
} from "./chatbotContext";
import type { RegionIndex } from "./types";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  sourceLabel?: string;
  followUps?: string[];
}

interface LlmConfig {
  enabled: boolean;
  endpoint: string;
  model: string;
  apiKey: string;
}

const STORAGE_KEY = "fieldwitness_chatbot_llm_cfg_v1";
const ENV_PROXY_URL = (import.meta.env.VITE_CHATBOT_PROXY_URL as string | undefined)?.trim() || "";
const ENV_MODEL = (import.meta.env.VITE_CHATBOT_MODEL as string | undefined)?.trim() || "gemini-2.5-flash";

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  text: "Hello! I am the FieldWitness Context Assistant. Ask me about the Three Witnesses, Evidence Grades A–D, USDA SSURGO soil TAW, winter wheat calibration, climate what-ifs, or any field you open.",
  sourceLabel: "FieldWitness Assistant [O/D/E]",
  followUps: ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
};

function loadLlmConfig(): LlmConfig {
  const defaultCfg: LlmConfig = {
    enabled: Boolean(ENV_PROXY_URL),
    endpoint:
      ENV_PROXY_URL ||
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    model: ENV_MODEL,
    apiKey: "",
  };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<LlmConfig>;
      return {
        enabled: parsed.enabled !== undefined ? Boolean(parsed.enabled) : defaultCfg.enabled,
        endpoint: parsed.endpoint || defaultCfg.endpoint,
        model: parsed.model || defaultCfg.model,
        apiKey: parsed.apiKey || "",
      };
    }
  } catch {
    // ignore storage errors
  }
  return defaultCfg;
}

/** Renders safe inline Markdown (**bold**, `code`) and newlines without dangerouslySetInnerHTML. */
function renderInlineTokens(line: string): ReactNode[] {
  const tokens = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return tokens.map((tok, i) => {
    if (tok.startsWith("**") && tok.endsWith("**") && tok.length > 4) {
      return <strong key={i}>{tok.slice(2, -2)}</strong>;
    }
    if (tok.startsWith("`") && tok.endsWith("`") && tok.length > 2) {
      return <code key={i}>{tok.slice(1, -1)}</code>;
    }
    return <Fragment key={i}>{tok}</Fragment>;
  });
}

function renderChatText(text: string): ReactNode {
  const lines = text.split("\n");
  return lines.map((line, idx) => (
    <Fragment key={idx}>
      {renderInlineTokens(line)}
      {idx < lines.length - 1 && <br />}
    </Fragment>
  ));
}

async function callLlmEndpoint(
  cfg: LlmConfig,
  systemPrompt: string,
  history: { role: "user" | "assistant"; content: string }[],
  userQuery: string,
  maxTokens = 700,
): Promise<string> {
  let url = cfg.endpoint.trim();
  const key = cfg.apiKey.trim();
  const isGeminiNative = url.includes("generativelanguage.googleapis.com") && url.includes(":generateContent");

  if (isGeminiNative) {
    if (cfg.model.trim() && url.includes("/models/")) {
      url = url.replace(/\/models\/[^:]+:/, `/models/${encodeURIComponent(cfg.model.trim())}:`);
    }
    if (key && !url.includes("key=")) {
      url += `${url.includes("?") ? "&" : "?"}key=${encodeURIComponent(key)}`;
    }
    const contents = [
      ...history.map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      })),
      { role: "user", parts: [{ text: userQuery }] },
    ];
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: systemPrompt }] },
        contents,
        generationConfig: { temperature: 0.2, maxOutputTokens: maxTokens },
      }),
      signal: AbortSignal.timeout(20000),
    });
    if (!res.ok) {
      const errBody = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}${errBody ? `: ${errBody.slice(0, 140)}` : ""}`);
    }
    const data = await res.json();
    const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (typeof reply === "string" && reply.trim()) return reply.trim();
    throw new Error("Gemini HTTP 200 returned no text candidate");
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (key) {
    headers.Authorization = `Bearer ${key}`;
  }
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: cfg.model || ENV_MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        ...history,
        { role: "user", content: userQuery },
      ],
      temperature: 0.2,
      max_tokens: maxTokens,
    }),
    signal: AbortSignal.timeout(20000),
  });
  if (!res.ok) {
    const errBody = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}${errBody ? `: ${errBody.slice(0, 140)}` : ""}`);
  }
  const data = await res.json();
  const reply = data?.choices?.[0]?.message?.content;
  if (typeof reply === "string" && reply.trim()) return reply.trim();
  throw new Error("HTTP 200 returned no choices[0].message.content");
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
  const [showSettings, setShowSettings] = useState(false);
  const [liveState, setLiveState] = useState<LiveChatStoreState>(() => getLiveChatState());
  const [llmCfg, setLlmCfg] = useState<LlmConfig>(() => loadLlmConfig());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [testStatus, setTestStatus] = useState<{ state: "idle" | "testing" | "ok" | "error"; message: string }>({
    state: "idle",
    message: "",
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => [WELCOME_MESSAGE]);

  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return subscribeLiveChatState(setLiveState);
  }, []);

  useEffect(() => {
    if (isOpen && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) setIsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  const activePack = fieldId ? liveState.fieldPack : null;
  const fieldLabel = resolveFieldLabel(activePack, index);
  const ctx: ChatContextSnapshot = {
    page: fieldId ? "field" : page || "map",
    regionId,
    fieldId,
    fieldNumberLabel: fieldLabel,
    fieldPack: activePack,
    fieldCalendar: fieldId ? liveState.fieldCalendar : null,
    fieldScenarios: fieldId ? liveState.fieldScenarios : null,
    priorities: fieldId ? liveState.priorities : null,
    hindcast: page === "scoreboard" ? liveState.hindcast : null,
    liveProfile: page === "add-field" ? liveState.liveProfile : null,
  };

  const contextSummary = activePack
    ? `Field ${fieldLabel ?? activePack.field.field_id.slice(0, 8)} (${activePack.field.area_ha.toFixed(1)} ha)`
    : ctx.liveProfile
      ? `Global (${ctx.liveProfile.latitude.toFixed(2)}, ${ctx.liveProfile.longitude.toFixed(2)})`
      : `${ctx.page.toUpperCase()} · ${regionId}`;

  const saveLlmConfig = (next: LlmConfig) => {
    setLlmCfg(next);
    setTestStatus({ state: "idle", message: "" });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore storage errors
    }
  };

  const handleTestConnection = async () => {
    if (!llmCfg.endpoint.trim()) {
      setTestStatus({ state: "error", message: "Enter an endpoint URL first." });
      return;
    }
    setTestStatus({ state: "testing", message: "Sending test request..." });
    try {
      const reply = await callLlmEndpoint(llmCfg, "Reply briefly.", [], "Reply with OK", 24);
      saveLlmConfig({ ...llmCfg, enabled: true });
      setTestStatus({
        state: "ok",
        message: `Connected! Reply: "${reply.slice(0, 60)}"`,
      });
    } catch (err) {
      setTestStatus({
        state: "error",
        message: err instanceof Error ? `Failed: ${err.message}` : "Network or CORS error",
      });
    }
  };

  const handleSend = async (rawText?: string) => {
    const query = (rawText ?? input).trim();
    if (!query || isLoading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!rawText) setInput("");

    if (llmCfg.enabled && llmCfg.endpoint.trim()) {
      setIsLoading(true);
      try {
        const history = messages
          .filter((m) => m.id !== "welcome")
          .slice(-6)
          .map((m) => ({ role: m.role, content: m.text }));
        const reply = await callLlmEndpoint(llmCfg, buildSystemPrompt(ctx), history, query, 700);
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: "assistant",
            text: reply,
            sourceLabel: `LLM (${llmCfg.model || ENV_MODEL}) · Full Context`,
          },
        ]);
        setIsLoading(false);
        return;
      } catch (err) {
        const errHint = err instanceof Error ? err.message : "Network or CORS error";
        setIsLoading(false);
        const ans = answerQuestion(query, ctx);
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: "assistant",
            text: `${ans.text}\n\n[LLM fallback reason: ${errHint}]`,
            sourceLabel: "Grounded Fallback (LLM Error)",
            followUps: ans.followUps,
          },
        ]);
        return;
      }
    }

    const ans = answerQuestion(query, ctx);
    setMessages((prev) => [
      ...prev,
      {
        id: `a-${Date.now()}`,
        role: "assistant",
        text: ans.text,
        sourceLabel: ans.sourceLabel,
        followUps: ans.followUps,
      },
    ]);
  };

  return (
    <div className="chatbot-root">
      {isOpen && (
        <section className="chatbot-drawer" aria-label="FieldWitness Context Assistant">
          <header className="chatbot-header">
            <div className="chatbot-title-wrap">
              <strong className="chatbot-title">FieldWitness Assistant</strong>
              <span className="chatbot-ctx-pill" title="Live active context">
                {contextSummary}
              </span>
            </div>
            <div className="chatbot-header-actions">
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={() => setMessages([WELCOME_MESSAGE])}
                aria-label="Reset conversation"
                title="Clear conversation"
              >
                Reset
              </button>
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={() => setShowSettings((s) => !s)}
                aria-label="Assistant API settings"
                title="Optional LLM API Settings"
              >
                API
              </button>
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Close assistant"
              >
                ✕
              </button>
            </div>
          </header>

          {showSettings && (
            <div className="chatbot-settings">
              <p className="chatbot-settings-note">
                Built-in Grounded Mode works offline for free. For generative LLM answers, pick a preset (or enter a proxy URL) and paste your API key (stored in browser only):
              </p>
              <div className="chatbot-chips" style={{ marginBottom: "0.35rem" }}>
                <button
                  type="button"
                  className="chatbot-chip"
                  onClick={() =>
                    saveLlmConfig({
                      ...llmCfg,
                      enabled: true,
                      endpoint:
                        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                      model: "gemini-2.5-flash",
                    })
                  }
                >
                  Gemini Native (AI Studio)
                </button>
                <button
                  type="button"
                  className="chatbot-chip"
                  onClick={() =>
                    saveLlmConfig({
                      ...llmCfg,
                      enabled: true,
                      endpoint: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                      model: "gemini-2.5-flash",
                    })
                  }
                >
                  Gemini (OpenAI-compat)
                </button>
                <button
                  type="button"
                  className="chatbot-chip"
                  onClick={() =>
                    saveLlmConfig({
                      ...llmCfg,
                      enabled: true,
                      endpoint: "https://api.openai.com/v1/chat/completions",
                      model: "gpt-4o-mini",
                    })
                  }
                >
                  OpenAI
                </button>
                <button
                  type="button"
                  className="chatbot-chip"
                  onClick={() =>
                    saveLlmConfig({
                      ...llmCfg,
                      enabled: true,
                      endpoint: "https://api.deepseek.com/chat/completions",
                      model: "deepseek-chat",
                    })
                  }
                >
                  DeepSeek
                </button>
              </div>
              <label className="chatbot-check">
                <input
                  type="checkbox"
                  checked={llmCfg.enabled}
                  onChange={(e) => saveLlmConfig({ ...llmCfg, enabled: e.target.checked })}
                />
                Use LLM Endpoint
              </label>
              <input
                type="url"
                className="chatbot-setting-input"
                placeholder="Proxy, Gemini Native, or OpenAI-compatible URL"
                value={llmCfg.endpoint}
                onChange={(e) => saveLlmConfig({ ...llmCfg, endpoint: e.target.value })}
              />
              <input
                type="text"
                className="chatbot-setting-input"
                placeholder="Model (e.g. gemini-2.5-flash, gpt-4o-mini)"
                value={llmCfg.model}
                onChange={(e) => saveLlmConfig({ ...llmCfg, model: e.target.value })}
              />
              <input
                type="password"
                className="chatbot-setting-input"
                placeholder="API Key (optional if using a server proxy)"
                value={llmCfg.apiKey}
                onChange={(e) => saveLlmConfig({ ...llmCfg, apiKey: e.target.value })}
              />
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.25rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="chatbot-chip"
                  onClick={handleTestConnection}
                  disabled={testStatus.state === "testing"}
                >
                  {testStatus.state === "testing" ? "Testing..." : "Test Connection"}
                </button>
                {testStatus.state !== "idle" && (
                  <span
                    role="status"
                    style={{
                      fontSize: "0.75rem",
                      color:
                        testStatus.state === "ok"
                          ? "#16a34a"
                          : testStatus.state === "error"
                            ? "#dc2626"
                            : "inherit",
                    }}
                  >
                    {testStatus.message}
                  </span>
                )}
              </div>
            </div>
          )}

          <div className="chatbot-messages" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`chatbot-msg chatbot-msg--${m.role}`}>
                <div className="chatbot-bubble">
                  <p className="chatbot-text">{renderChatText(m.text)}</p>
                  {m.sourceLabel && <span className="chatbot-source">{m.sourceLabel}</span>}
                </div>
                {m.role === "assistant" && m.followUps && m.followUps.length > 0 && (
                  <div className="chatbot-chips">
                    {m.followUps.map((chip) => (
                      <button
                        key={chip}
                        type="button"
                        className="chatbot-chip"
                        onClick={() => handleSend(chip)}
                      >
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
                  <p className="chatbot-text">Thinking with project context...</p>
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
              placeholder={
                activePack
                  ? `Ask about Field ${fieldLabel ?? ""} or FieldWitness...`
                  : "Ask about witnesses, grades, soil, wheat..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              aria-label="Ask FieldWitness question"
            />
            <button type="submit" className="chatbot-send-btn" disabled={!input.trim() || isLoading}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className="chatbot-fab"
        onClick={() => {
          setIsOpen((o) => !o);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        aria-expanded={isOpen}
        aria-label="Ask FieldWitness Assistant"
      >
        {isOpen ? "Close Chat" : "Ask FieldWitness"}
      </button>
    </div>
  );
}
