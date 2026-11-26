# Reeves dialogue architecture

**Status:** PROPOSED / BETA prototype

**Public frontend:** GitHub Pages

**Dialogue backend:** separate API (Cloudflare Worker or optional `reeves_api` service)

**Normative receiver:** unchanged ROZUM_AI_v2.1 runtime

## Implemented in this branch

1. The static Pages site and its local 21-topic Ukrainian/Russian knowledge
   engine remain available without a server.
2. `assets/assistant-core.js` classifies the local engine result as
   `project_knowledge` or `general_dialogue`, attaches a known topic ID when
   available, and keeps the browser UI and backend on the same route contract.
3. The browser sends only the current message, bounded history, and optional
   route/topic metadata when the public feature flag is enabled. Provider
   credentials never enter Pages assets.
4. The route/topic hint is advisory retrieval metadata, not evidence and not a
   signed `ROZUM_AI_v2` envelope. The API maps known topics to allowlisted public
   documents and returns only source names actually used.
5. A failed, timed-out or malformed server response falls back to the local
   knowledge engine. The local fallback states when the open ROZUM material has
   no answer instead of inventing one.
6. Reeves owns dialogue wording. Argos reports only request checks that ran.
   Andromeda is not activated for ordinary chat.
7. Optional browser memory is off by default. After explicit consent, at most
   40 sanitized turns are kept in same-origin browser storage; the user can
   inspect and delete them. The API service persists no prompt history.
8. The Cloudflare Worker enforces an origin allowlist, actual body-size limits,
   bounded history and a best-effort per-isolate sliding-window rate limit. The
   optional Python service also keeps provider credentials server-side and
   rejects chat requests from missing or unapproved browser origins.
9. The Worker retrieves at most two status-attributed public ROZUM documents.
   The public Pages configuration is enabled and points to the deployed
   Cloudflare Worker. The local knowledge engine remains the automatic fallback.
10. The browser accepts citation links only from the public ROZUM repository and
    rejects malformed or oversized model replies before rendering them.

## Trust boundaries

```text
Browser / GitHub Pages
  ├─ local knowledge engine (always available)
  ├─ opt-in local history (user can inspect/delete)
  └─ HTTPS request without credentials
          │
          ▼
Dialogue API (Cloudflare Worker or optional Python service)
  ├─ request limits + rate limit
  ├─ Argos guard report
  ├─ allowlisted ROZUM source retrieval
  └─ no prompt-history persistence in the service
          │
          ▼
Configured model provider (active public beta)
```

The normative v2.1 receiver remains a separate protocol service. The site-level
ROZUM Core bridge only supplies bounded route/topic metadata to the dialogue
backend. It does not create a packet, sign a message, or claim that ordinary chat
passed the v2.1 receiver's five-stage validation. The public beta may discuss
proposed v2.2 ideas, but the repository schema and receiver remain v2.1.

## Remaining limits before a wider public launch

- replace the per-isolate limiter with a shared rate/cost store;
- configure and verify an account-level daily budget cutoff and circuit breaker;
- review Cloudflare AI Gateway and third-party search logging before enabling
  web search by default;
- complete the legal/license review and publish a stable contact path;
- run sustained load, abuse and prompt-injection tests in Ukrainian and Russian;
- preserve the mock/local fallback when the provider is unavailable.

Current beta controls already in place:

- the Workers AI binding keeps provider credentials out of Pages assets;
- each model response is capped at 500 completion tokens;
- web search code is opt-in and separately rate-limited, while the public
  `webSearchEnabled` / `WEB_SEARCH_ENABLED` flags remain false until AI Gateway
  credits or a provider key are configured;
- the Worker requests `store: false` and does not write prompt history to
  application storage;
- `/healthz` reports process liveness, while `/readyz` fails closed when the
  Workers AI binding is unavailable.

The current in-memory limiter and Cloudflare free daily allocation reduce casual
cost exposure but are not a globally shared budget or authentication mechanism.

## Deployment history and next release

Completed for the current beta:

- the Cloudflare Worker is deployed;
- `assets/assistant-config.js` enables its HTTPS URL;
- live `/healthz`, `/readyz`, CORS and bilingual fallback behavior were checked;
- the privacy notice identifies remote model processing and the currently
  disabled external search path.

For the next release:

- run the complete local regression and dependency audit;
- review the diff and privacy wording;
- deploy the Worker before the Pages client if the API contract changed;
- verify live health, readiness, CORS, fallback and both languages after deploy;
- roll back to the previous Worker/Pages revision if any check fails.

## Historical pre-deployment checklist

The following items were the original prototype gate and are retained as
history, not as a statement of current deployment state:

- choose the model and set a reviewed usage budget;
- store the provider key in the backend host's secret manager;
- replace the in-memory limiter with a shared rate/cost store;
- configure a daily budget cutoff, per-request token ceiling and circuit breaker;
- define prompt-retention and abuse-review policy without body logging;
- verify the backend host, HTTPS, CORS origin and failover path;
- review the privacy notice and evaluate prompt injection and citations in
  Ukrainian and Russian;
- keep the mock/local fallback available when the provider is unavailable.
