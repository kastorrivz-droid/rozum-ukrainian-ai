# Reeves dialogue architecture

**Status:** PROPOSED / BETA prototype

**Public frontend:** GitHub Pages

**Dialogue backend:** separate `reeves_api` service

**Normative receiver:** unchanged ROZUM_AI_v2.1 runtime

## Implemented in this branch

1. The existing static design remains the default and works without a server.
2. The browser can call `POST /v1/chat` only when the public, non-secret feature
   flag is enabled. Provider credentials never enter Pages assets.
3. A failed, timed-out or malformed server response falls back to the local
   21-topic Ukrainian/Russian engine.
4. Reeves owns dialogue wording. Argos reports request-contract and policy
   checks. Andromeda is not activated for ordinary chat.
5. Optional browser memory is off by default. After explicit consent, at most
   40 sanitized turns are kept in same-origin browser storage; the user can
   inspect and delete them. The prototype server persists no prompt history.
6. The server enforces an origin allowlist, actual body-size limits, strict
   UTF-8 JSON, duplicate-key rejection, bounded history, provider allowlisting
   and a single-process sliding-window rate limit.

## Trust boundaries

```text
Browser / GitHub Pages
  ├─ local knowledge engine (always available)
  ├─ opt-in local history (user can inspect/delete)
  └─ HTTPS request without credentials
          │
          ▼
Reeves API
  ├─ request limits + rate limit
  ├─ Argos guard report
  ├─ provider adapter (mock only today)
  └─ no prompt persistence
          │
          ▼
Paid model provider (not connected in this branch)
```

The v2.1 receiver remains a separate protocol service. The public site mentions
v2.2, but the repository schema and receiver are still v2.1. This branch does
not silently relabel that receiver. A future v2.2 knowledge adapter must import
versioned, source-attributed material without changing v2.1 signing semantics.

## Required before an internet-facing model

- choose the model provider and a hard daily/monthly spend ceiling;
- store the provider key in the deployment secret manager;
- replace the in-memory limiter with a shared rate/cost store;
- add per-request token ceilings, daily budget cutoff and circuit breaker;
- define prompt-retention and abuse-review policy without body logging;
- test the exact deployment target, CORS origin and failover path;
- run prompt-injection and knowledge-citation evaluation in Ukrainian/Russian;
- keep the mock/local fallback available when the budget or provider is down.

## Release sequence

1. Push this feature branch and require CI.
2. Review the Pages visual diff and the separate backend configuration.
3. Merge static/local improvements without enabling an absent API.
4. Deploy the mock backend and verify `/readyz` from the target environment.
5. Add a paid provider adapter behind the same contract and test it with a
   capped beta budget.
6. Enable `apiBaseUrl` only after the deployed API, cost guard and privacy text
   are verified.
