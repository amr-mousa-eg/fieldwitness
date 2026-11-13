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

function loadLlmConfig(): LlmConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<LlmConfig>;
      return {
        enabled: Boolean(parsed.enabled),
        endpoint: parsed.endpoint || "https://api.openai.com/v1/chat/completions",
        model: parsed.model || "gpt-4o-mini",
        apiKey: parsed.apiKey || "",
      };
    }
  } catch {
    // ignore storage errors
  }
  return {
    enabled: false,
    endpoint: "https://api.openai.com/v1/chat/completions",
    model: "gpt-4o-mini",
    apiKey: "",
  };
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

    if (llmCfg.enabled && llmCfg.endpoint && llmCfg.apiKey) {
      setIsLoading(true);
      try {
        const res = await fetch(llmCfg.endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${llmCfg.apiKey}`,
          },
          body: JSON.stringify({
            model: llmCfg.model || "gpt-4o-mini",
            messages: [
              { role: "system", content: buildSystemPrompt(ctx) },
              { role: "user", content: query },
            ],
            temperature: 0.2,
          }),
          signal: AbortSignal.timeout(15000),
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
      } catch {
        // Fallback cleanly to built-in grounded advisor
      }
      setIsLoading(false);
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
                Built-in Grounded Mode works offline for free. Optionally connect your own OpenAI-compatible API key (stored in browser only):
              </p>
              <label className="chatbot-check">
                <input
                  type="checkbox"
                  checked={llmCfg.enabled}
                  onChange={(e) => saveLlmConfig({ ...llmCfg, enabled: e.target.checked })}
                />
                Use Custom LLM Endpoint
              </label>
              <input
                type="url"
                className="chatbot-setting-input"
                placeholder="Endpoint URL (e.g. https://api.openai.com/v1/chat/completions)"
                value={llmCfg.endpoint}
                onChange={(e) => saveLlmConfig({ ...llmCfg, endpoint: e.target.value })}
              />
              <input
                type="text"
                className="chatbot-setting-input"
                placeholder="Model (e.g. gpt-4o-mini)"
                value={llmCfg.model}
                onChange={(e) => saveLlmConfig({ ...llmCfg, model: e.target.value })}
              />
              <input
                type="password"
                className="chatbot-setting-input"
                placeholder="API Key (stored locally in browser)"
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
