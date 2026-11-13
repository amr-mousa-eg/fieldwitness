# FieldWitness chat proxy (Cloudflare Worker, free plan)

Holds the LLM API key server-side so the static site (GitHub Pages) can offer the "Ask FieldWitness"
assistant to everyone with **no key in the repo, the build or the browser**.

What it does (`src/index.ts`):

- CORS allowlist: `https://amr-mousa-eg.github.io`, `http://localhost:*`, `http://127.0.0.1:*`.
  Any other origin gets 403. `OPTIONS` preflight is handled.
- Accepts only `{"messages": [...]}`: at most 8 messages, roles `system`/`user`/`assistant`, last
  one from the user, at most 12,000 characters in total. Anything else gets a 4xx JSON error
  `{"error": {"code", "message"}}`. Client-sent `model`, `temperature`, `max_tokens` or endpoint
  are ignored.
- Fixes on the server: model (`LLM_MODEL`), temperature 0.2, `max_tokens` 400 (`MAX_TOKENS`).
- Abuse protection: per-IP limit of 10 questions per 60 s with the Workers **Rate Limiting binding**
  (`[[ratelimits]]` in `wrangler.toml`), plus an optional global **daily cap** (default 500) kept in
  a **KV namespace**. Both return 429 with `Retry-After`.
  The Cloudflare docs say rate-limit counts are approximate and per location; they do not say
  whether the binding is on the Free plan (UNVERIFIED — if `wrangler deploy` rejects it, delete the
  `[[ratelimits]]` block and rely on the KV daily cap). KV on the Free plan allows 1,000 writes per
  day, so keep `DAILY_CAP` below about 900.
- Never forwards upstream error bodies or headers; returns a short code (`upstream_error`,
  `upstream_timeout`, `upstream_rate_limited`, …).
- Replies in OpenAI shape: `{"choices": [{"message": {"role": "assistant", "content": "..."}}]}`.

## Deploy (you run these; run them from this folder)

```bash
cd workers/chat-proxy
```

```bash
npx wrangler login
```

```bash
npx wrangler kv namespace create USAGE
```

Paste the printed `id` into the commented `[[kv_namespaces]]` block in `wrangler.toml` and
uncomment it (optional but recommended; it enables the daily cap).

```bash
npx wrangler secret put LLM_API_KEY
```

Paste your Google AI Studio key (or Groq key) at the prompt. It is stored encrypted by Cloudflare,
never in git.

```bash
npx wrangler deploy
```

Wrangler prints the Worker URL, e.g. `https://fieldwitness-chat-proxy.<your-subdomain>.workers.dev`.
Then point the website at it (repository variable, read by `.github/workflows/pages.yml`):

```bash
gh variable set VITE_CHATBOT_PROXY_URL --body "https://fieldwitness-chat-proxy.<your-subdomain>.workers.dev"
```

and re-run the Pages workflow (or push to `main`) so the site is rebuilt with the URL.

Quick check (should print a JSON reply; uses the allowed origin):

```bash
curl -s -X POST "https://fieldwitness-chat-proxy.<your-subdomain>.workers.dev" -H "Origin: https://amr-mousa-eg.github.io" -H "Content-Type: application/json" -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in five words.\"}]}"
```

## Providers (switch with no code change)

Edit `[vars]` in `wrangler.toml`, put the matching key with `wrangler secret put LLM_API_KEY`,
then `npx wrangler deploy`.

| Provider | `LLM_BASE_URL` | `LLM_MODEL` (default) | Key from |
|---|---|---|---|
| Google Gemini (default) | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-3.5-flash-lite` | aistudio.google.com |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | console.groq.com |

Both were checked against the official docs on 2026-11-13 (`docs/api_notes.md`). Google's pricing
page lists `gemini-3.5-flash-lite` as "Free of charge" on the free tier; the exact free-tier RPM/RPD
for it is shown only inside AI Studio (UNVERIFIED here). Groq's per-model free limits are shown only
in the account's limits page (UNVERIFIED here). If Gemini replies come back empty, uncomment
`LLM_REASONING_EFFORT = "low"`.

**Privacy:** Google's pricing page says free-tier content is "used to improve our products". The
app shows a notice under the chat input. Groq's data terms were not checked (UNVERIFIED).

## Tests

```bash
node --test test/proxy.test.ts
```

Plain Node (>= 23.6, which strips TypeScript types); no dependencies.
