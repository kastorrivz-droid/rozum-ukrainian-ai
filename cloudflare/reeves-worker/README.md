# ROZUM Assistant: free model test

This directory contains the Cloudflare Worker API used by the GitHub Pages chat. The browser configuration points to the deployed Worker and keeps the local knowledge engine as a fallback.

## ROZUM Core dialogue bridge

The browser runs `assets/assistant-core.js` after the local knowledge engine. It classifies a turn as `project_knowledge` or `general_dialogue` and, when known, attaches a short topic ID. The optional `core_context` request field is bounded routing metadata only; it is not a signed `ROZUM_AI_v2` packet and is never treated as evidence. The Worker uses an allowlisted topic-to-document map to improve retrieval, then returns the route and the names of the source excerpts it actually used.

The normative ROZUM_AI_v2.1 receiver remains a separate protocol service. Ordinary chat does not invoke its signature or replay validation pipeline.

## Model and free-plan limit

- Model: `@cf/google/gemma-4-26b-a4b-it` through Cloudflare Workers AI.
- Google describes Gemma 4 as supporting more than 140 languages.
- Cloudflare Workers Free includes 10,000 Neurons per day for Workers AI. The daily allocation resets at 00:00 UTC. On the Free plan, requests stop when the allocation is exhausted; the quota is not unlimited.
- Keep the Cloudflare account on the Free plan for this test. Paid-plan usage above the free allocation is billed.
- No model-provider key is stored in this repository. The AI binding is configured in `wrangler.jsonc`.
- The Worker explicitly requests non-stored output, disables Gemma's reasoning mode for reliable concise chat answers, and caps each answer at 500 completion tokens.

Official references:
- [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Gemma 4 on Workers AI](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/)

## Optional web search

The chat exposes a user-controlled **Пошук в інтернеті** switch. When enabled, the Worker calls Cloudflare Web Search through the existing AI binding, using the Ceramic.ai provider and at most five results. No search key is sent to the browser or stored in this repository. Search requires AI Gateway credits or a provider key stored securely in AI Gateway; if billing is not configured or the provider fails, Reeves continues without live results and must say that current information was not verified.

Search snippets are treated as untrusted external data, sanitized, bounded, and labeled `EXTERNAL / UNVALIDATED`. They never become accepted ROZUM facts automatically. The Worker does not fetch result URLs, which avoids user-controlled server-side URL requests. A separate best-effort per-isolate limit allows four search requests per minute per IP.

Official references:
- [Cloudflare Web Search API](https://developers.cloudflare.com/web-search/)
- [Workers binding and response contract](https://developers.cloudflare.com/web-search/how-to-use/)
- [Search providers and pricing](https://developers.cloudflare.com/web-search/providers/)

## Local contract check

From the repository root, run:

```sh
node --test cloudflare/reeves-worker/test.mjs
```

These tests mock the Workers AI and Web Search bindings and check the HTTP response contract, source sanitization, language handling, and origin restrictions. They do not call live providers.

The AI binding is marked `remote: true`, so `wrangler dev` uses the real account binding while the HTTP Worker still runs locally. Live model tests consume the account's Workers AI allocation.

## Deploy from Windows PowerShell

Install Node.js if it is not already installed, then from the repository root run:

```powershell
Set-Location .\cloudflare\reeves-worker
npx wrangler@latest login
npx wrangler@latest deploy
```

The first command opens Cloudflare authentication. The deploy command prints the public Worker URL, usually shaped like:

```
https://rozum-reeves-api.<your-workers-subdomain>.workers.dev
```

This Worker exposes `GET /healthz`, `GET /readyz`, and `POST /v1/chat`. Test the public health route first. For a model request, use the Worker URL with `/v1/chat`, JSON containing `message`, `language`, `history`, and optionally `web_search: true` and `core_context: { route, topic_id }`, plus the `Origin: https://kastorrivz-droid.github.io` header. The browser sends only the bounded route and topic ID; it does not send a protocol signature.

## Connect the website after deployment

After the Worker is deployed and its URL is known, set `assets/assistant-config.js` to:

```js
apiEnabled: true,
apiBaseUrl: 'https://rozum-reeves-api.<your-workers-subdomain>.workers.dev',
requestTimeoutMs: 25000
```

Use the actual URL printed by Wrangler. This configuration is public but contains no secret. The existing client falls back to its local knowledge engine if the Worker or model is unavailable.

## Data and public-test limits

The Worker does not write conversation history to storage. It sends the current message, up to eight recent turns, the bounded ROZUM Core route/topic hint, and up to two relevant public ROZUM documents to Workers AI. When the user explicitly enables web search, the search query is also processed by Cloudflare AI Gateway and Ceramic.ai, and sanitized result snippets are passed to the model. The website displays this in its privacy notice; provider processing is subject to their terms.

CORS allows the GitHub Pages origin and local development on ports 4173. This is a browser boundary, not authentication: the Worker URL is public. A per-IP in-memory limiter is best-effort per Worker isolate, while Cloudflare's daily free allocation is the hard quota. Keep this as a small beta test and do not put secrets or personal data in chat.
