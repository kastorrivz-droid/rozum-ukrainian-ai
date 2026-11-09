# Reeves API prototype

**Status:** PROPOSED / local integration prototype

This service is separate from the normative ROZUM_AI_v2.1 receiver. It gives
the static GitHub Pages assistant a server-side dialogue boundary without
placing provider credentials in browser code.

## Current contract

- \`GET /healthz\` — process liveness;
- \`GET /readyz\` — provider readiness without secrets;
- \`POST /v1/chat\` — bounded Ukrainian/Russian dialogue request;
- deterministic \`mock\` provider remains the default;
- optional OpenAI Responses adapter, selected explicitly with
  \`REEVES_PROVIDER=openai\`;
- the OpenAI adapter retrieves at most two relevant public project documents
  from the repository checkout and returns their existing statuses as citations;
- the provider request includes the current message and at most eight recent,
  length-limited turns; it does not write prompt history to this service;
- Argos guard report is distinct from the Reeves response role;
- real request-byte limit, CORS allowlist and single-process rate limit;
- browser automatically falls back to the local 21-topic engine.

The browser also has separate opt-in local memory: it is disabled by default,
bounded to 40 turns, visible to the user and deletable in one action.

## Local mock run

From the repository root:

\`\`\`powershell
$env:PYTHONPATH = 'src'
$env:REEVES_PROVIDER = 'mock'
$env:REEVES_ALLOWED_ORIGINS = 'http://127.0.0.1:8000'
python -m uvicorn reeves_api.app:app --host 127.0.0.1 --port 8787
\`\`\`

## Select the OpenAI provider

Configure these values in the backend host's environment settings:

- \`REEVES_PROVIDER=openai\`;
- \`OPENAI_API_KEY\` as a host-managed secret;
- \`OPENAI_MODEL\` as a model enabled for the API project;
- optional \`REEVES_MAX_OUTPUT_TOKENS=500\`;
- \`REEVES_ALLOWED_ORIGINS=https://kastorrivz-droid.github.io\`.

The key must never go in GitHub Pages assets, the repository, a screenshot, or a
browser request. The frontend configuration remains public and secret-free:
set \`apiEnabled: true\` and the deployed HTTPS \`apiBaseUrl\` only after the
backend, privacy notice and cost controls are ready.

## Production boundary

The in-memory limiter is suitable only for one beta process. Before public
model traffic, configure a shared rate/cost limiter, a daily budget cutoff,
provider-side usage limits, a circuit breaker, abuse monitoring that does not
log prompt bodies, and an explicit retention policy. The model receives the
current user message, up to eight recent turns, and selected public project
excerpts. OpenAI API data handling still applies to those requests. Keep the
mock/local fallback available when the provider or budget is unavailable.
