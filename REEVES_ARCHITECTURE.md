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
   optional Python service also keeps provider credentials server-side.
9. The Worker retrieves at most two status-attributed public ROZUM documents.
   The public Pages configuration remains disabled until a backend is deployed
   and the privacy and usage limits are reviewed.

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
Configured model provider (not active on the public site)
```

The normative v2.1 receiver remains a separate protocol service. The site-level
ROZUM Core bridge only supplies bounded route/topic metadata to the dialogue
backend. It does not create a packet, sign a message, or claim that ordinary chat
passed the v2.1 receiver's five-stage validation. The public beta may discuss
proposed v2.2 ideas, but the repository schema and receiver remain v2.1.

## Required before public model traffic

- choose the model and set a reviewed usage budget;
- store the provider key in the backend host's secret manager;
- replace the in-memory limiter with a shared rate/cost store;
- configure a daily budget cutoff, per-request token ceiling and circuit breaker;
- define prompt-retention and abuse-review policy without body logging;
- verify the backend host, HTTPS, CORS origin and failover path;
- review the privacy notice and evaluate prompt injection and citations in
  Ukrainian and Russian;
- keep the mock/local fallback available when the provider is unavailable.

## Release sequence

1. Review the Pages visual, local fallback and privacy-text changes.
2. Merge the code while `apiEnabled` remains false.
3. Deploy the Cloudflare Worker on the Free plan and verify `/healthz`, `/readyz`,
   CORS and fallback behavior; confirm the free quota and best-effort limiter.
4. Enable `apiBaseUrl` only after the deployed URL, privacy notice and usage
   limits have been reviewed. Keep provider keys out of Pages assets.
