# ROZUM Assistant: free model test

This directory contains a separate Cloudflare Worker API for the existing GitHub Pages chat. It does not switch the live site into remote mode; the site keeps using its local knowledge engine until its public configuration is deliberately updated.

## ROZUM Core dialogue bridge

The browser runs `assets/assistant-core.js` after the local knowledge engine. It classifies a turn as `project_knowledge` or `general_dialogue` and, when known, attaches a short topic ID. The optional `core_context` request field is bounded routing metadata only; it is not a signed `ROZUM_AI_v2` packet and is never treated as evidence. The Worker uses an allowlisted topic-to-document map to improve retrieval, then returns the route and the names of the source excerpts it actually used.

The normative ROZUM_AI_v2.1 receiver remains a separate protocol service. Ordinary chat does not invoke its signature or replay validation pipeline.

## Model and free-plan limit

- Model: `@cf/google/gemma-4-26b-a4b-it` through Cloudflare Workers AI.
- Google describes Gemma 4 as supporting more than 140 languages.
- Cloudflare Workers Free includes 10,000 Neurons per day for Workers AI. The daily allocation resets at 00:00 UTC. On the Free plan, requests stop when the allocation is exhausted; the quota is not unlimited.
- Keep the Cloudflare account on the Free plan for this test. Paid-plan usage above the free allocation is billed.
- No model-provider key is stored in this repository. The AI binding is configured in `wrangler.jsonc`.

Official references:
- [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Gemma 4 on Workers AI](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/)

## Local contract check

From the repository root, run:

```sh
node --test cloudflare/reeves-worker/test.mjs
```

These tests mock the Workers AI binding and check the HTTP response contract, language handling, and origin restrictions. They do not call the live model.

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

This Worker exposes `GET /healthz`, `GET /readyz`, and `POST /v1/chat`. Test the public health route first. For a model request, use the Worker URL with `/v1/chat`, JSON containing `message`, `language`, `history`, and optionally `core_context: { route, topic_id }`, and the `Origin: https://kastorrivz-droid.github.io` header. The browser sends only the bounded route and topic ID; it does not send a protocol signature.

## Connect the website after deployment

After the Worker is deployed and its URL is known, set `assets/assistant-config.js` to:

```js
apiEnabled: true,
apiBaseUrl: 'https://rozum-reeves-api.<your-workers-subdomain>.workers.dev',
requestTimeoutMs: 25000
```

Use the actual URL printed by Wrangler. This configuration is public but contains no secret. The existing client falls back to its local knowledge engine if the Worker or model is unavailable.

## Data and public-test limits

The Worker does not write conversation history to storage. It sends the current message, up to eight recent turns, the bounded ROZUM Core route/topic hint, and up to two relevant public ROZUM documents to Workers AI. The website displays a notice when remote mode is enabled; provider processing is subject to Cloudflare's terms.

CORS allows the GitHub Pages origin and local development on ports 4173. This is a browser boundary, not authentication: the Worker URL is public. A per-IP in-memory limiter is best-effort per Worker isolate, while Cloudflare's daily free allocation is the hard quota. Keep this as a small beta test and do not put secrets or personal data in chat.
