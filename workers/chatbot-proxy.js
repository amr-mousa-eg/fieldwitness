/**
 * FieldWitness Context Chatbot — Cloudflare Worker CORS Proxy
 *
 * Keeps your LLM API key off the static GitHub Pages frontend while enabling
 * zero-key generative answers for all visitors.
 *
 * Environment Variables / Secrets in Cloudflare Worker:
 *   - LLM_API_KEY (Secret, required): OpenAI / Gemini / Groq / OpenRouter API key
 *   - LLM_UPSTREAM_URL (Var, optional): defaults to OpenAI chat completions:
 *       OpenAI: https://api.openai.com/v1/chat/completions
 *       Gemini: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
 *       Groq:   https://api.groq.com/openai/v1/chat/completions
 *   - LLM_MODEL (Var, optional): overrides model sent by client (e.g. "gpt-4o-mini", "gemini-2.5-flash")
 *   - ALLOWED_ORIGIN (Var, optional): defaults to "https://amr-mousa-eg.github.io"
 */

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowedOrigin = env.ALLOWED_ORIGIN || "https://amr-mousa-eg.github.io";
    const isAllowed =
      origin === allowedOrigin ||
      origin.startsWith("http://localhost:") ||
      origin.startsWith("http://127.0.0.1:");

    const corsHeaders = {
      "Access-Control-Allow-Origin": isAllowed ? origin : allowedOrigin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (!env.LLM_API_KEY) {
      return new Response(JSON.stringify({ error: "Server proxy missing LLM_API_KEY" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const messages = Array.isArray(body?.messages) ? body.messages.slice(-10) : [];
    if (messages.length === 0) {
      return new Response(JSON.stringify({ error: "messages array is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const upstreamUrl =
      env.LLM_UPSTREAM_URL || "https://api.openai.com/v1/chat/completions";
    const model = env.LLM_MODEL || body?.model || "gpt-4o-mini";

    const upstreamRes = await fetch(upstreamUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.LLM_API_KEY}`,
      },
      body: JSON.stringify({
        model,
        messages,
        temperature: typeof body?.temperature === "number" ? body.temperature : 0.2,
        max_tokens: 600,
      }),
    });

    const responseText = await upstreamRes.text();
    return new Response(responseText, {
      status: upstreamRes.status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  },
};
