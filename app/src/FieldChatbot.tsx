import { useEffect, useRef, useState } from "react";
import {
  type ChatContextSnapshot,
  answerQuestion,
  buildSystemPrompt,
  getActiveFieldPack,
  resolveFieldLabel,
  subscribeActiveFieldPack,
} from "./chatbotContext";
import type { FieldPack, RegionIndex } from "./types";

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
const ENV_MODEL = (import.meta.env.VITE_CHATBOT_MODEL as string | undefined)?.trim() || "gpt-4o-mini";

function loadLlmConfig(): LlmConfig {
  const defaultCfg: LlmConfig = {
    enabled: Boolean(ENV_PROXY_URL),
    endpoint: ENV_PROXY_URL || "https://api.openai.com/v1/chat/completions",
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
  const [activePack, setActivePack] = useState<FieldPack | null>(() => getActiveFieldPack());
  const [llmCfg, setLlmCfg] = useState<LlmConfig>(() => loadLlmConfig());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: "welcome",
      role: "assistant",
      text: "Hello! I am the FieldWitness Context Assistant. Ask me about the Three Witnesses, Evidence Grades A–D, USDA SSURGO soil TAW, winter wheat calibration, or any field you open.",
      sourceLabel: "FieldWitness Assistant [O/D/E]",
      followUps: ["What is FieldWitness?", "How do the three witnesses work?", "What are the project's honest limits?"],
    },
  ]);

  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return subscribeActiveFieldPack((pack) => {
      setActivePack(pack);
    });
  }, []);

  useEffect(() => {
    if (!fieldId) {
      setActivePack(null);
    }
  }, [fieldId]);

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

  const saveLlmConfig = (next: LlmConfig) => {
    setLlmCfg(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore storage errors
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
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (llmCfg.apiKey.trim()) {
          headers.Authorization = `Bearer ${llmCfg.apiKey.trim()}`;
        }
        const history = messages
          .filter((m) => m.id !== "welcome")
          .slice(-6)
          .map((m) => ({ role: m.role, content: m.text }));

        const res = await fetch(llmCfg.endpoint.trim(), {
          method: "POST",
          headers,
          body: JSON.stringify({
            model: llmCfg.model || ENV_MODEL,
            messages: [
              { role: "system", content: buildSystemPrompt(ctx) },
              ...history,
              { role: "user", content: query },
            ],
            temperature: 0.2,
          }),
          signal: AbortSignal.timeout(20000),
        });
        if (res.ok) {
          const data = await res.json();
          const reply = data?.choices?.[0]?.message?.content;
          if (typeof reply === "string" && reply.trim()) {
            setMessages((prev) => [
              ...prev,
              {
                id: `a-${Date.now()}`,
                role: "assistant",
                text: reply.trim(),
                sourceLabel: `LLM (${llmCfg.model}) · Project Context`,
              },
            ]);
            setIsLoading(false);
            return;
          }
        }
        const errBody = await res.text().catch(() => "");
        const errHint = `LLM HTTP ${res.status}${errBody ? `: ${errBody.slice(0, 120)}` : ""}`;
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
                Built-in Grounded Mode works offline for free. For generative LLM answers, pick a provider preset (or enter a proxy URL) and paste your API key (stored in your browser only):
              </p>
              <div className="chatbot-chips" style={{ marginBottom: "0.35rem" }}>
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
                  Gemini (AI Studio)
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
                placeholder="Proxy or OpenAI-compatible URL"
                value={llmCfg.endpoint}
                onChange={(e) => saveLlmConfig({ ...llmCfg, endpoint: e.target.value })}
              />
              <input
                type="text"
                className="chatbot-setting-input"
                placeholder="Model (e.g. gpt-4o-mini, gemini-2.5-flash)"
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
            </div>
          )}

          <div className="chatbot-messages" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`chatbot-msg chatbot-msg--${m.role}`}>
                <div className="chatbot-bubble">
                  <p className="chatbot-text">{m.text}</p>
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
