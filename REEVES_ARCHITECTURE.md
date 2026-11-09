# Reeves dialogue architecture

**Status:** PROPOSED / BETA prototype

**Public frontend:** GitHub Pages

**Dialogue backend:** separate \`reeves_api\` service

**Normative receiver:** unchanged ROZUM_AI_v2.1 runtime

## Implemented in this branch

1. The static design remains the default and works without a server.
2. The browser calls \`POST /v1/chat\` only when the public, non-secret feature
   flag is enabled. Provider credentials never enter Pages assets.
3. A failed, timed-out or malformed server response falls back to the local
   21-topic Ukrainian/Russian engine.
4. Reeves owns dialogue wording. Argos reports request-contract and policy
   checks. Andromeda is not activated for ordinary chat.
5. Optional browser memory is off by default. After explicit consent, at most
   40 sanitized turns are kept in same-origin browser storage; the user can
   inspect and delete them. The API service persists no prompt history.
6. The server enforces an origin allowlist, actual body-size limits, strict
   UTF-8 JSON, duplicate-key rejection, bounded history, provider allowlisting
   and a single-process sliding-window rate limit.
7. The deterministic mock remains the default. An optional OpenAI Responses
   adapter runs only on the server when explicitly selected by environment.
8. The OpenAI adapter retrieves at most two relevant, status-attributed public
   ROZUM documents from the checked-out repository and sends a bounded context
   with the current message and recent turns. The public Pages configuration
   remains disabled until a backend is deployed and reviewed.

## Trust boundaries

\`\`\`text
Browser / GitHub Pages
  ├─ local knowledge engine (always available)
  ├─ opt-in local history (user can inspect/delete)
  └─ HTTPS request without credentials
          │
          ▼
Reeves API
  ├─ request limits + rate limit
  ├─ Argos guard report
  ├─ provider adapter (mock default; OpenAI optional)
  └─ no prompt-history persistence in the service
          │
          ▼
OpenAI Responses API (only when configured; not active on the public site)
\`\`\`

The v2.1 receiver remains a separate protocol service. The public site mentions
v2.2, but the repository schema and receiver are still v2.1. This branch does
not silently relabel that receiver. A future v2.2 knowledge adapter must import
versioned, source-attributed material without changing v2.1 signing semantics.

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

1. Push this feature branch and let repository CI run.
2. Review the Pages visual and privacy-text changes.
3. Merge the code while \`apiEnabled\` remains false.
4. Deploy the mock backend and verify \`/readyz\` from the chosen host.
5. Add the provider key as a host secret, choose the model, and configure the
   shared rate/cost controls.
6. Deploy the OpenAI adapter and verify its response and fallback paths.
7. Enable \`apiBaseUrl\` only after the service and privacy/cost settings are
   verified.
