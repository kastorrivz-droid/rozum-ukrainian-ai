# Reeves API prototype

**Status:** PROPOSED / local integration prototype

This service is separate from the normative ROZUM_AI_v2.1 receiver. It gives
the static GitHub Pages assistant a server-side dialogue boundary without
placing a provider key in browser code.

## Current contract

- `GET /healthz` — process liveness;
- `GET /readyz` — provider readiness without secrets;
- `POST /v1/chat` — bounded Ukrainian/Russian dialogue request;
- deterministic `mock` provider only;
- Argos guard report is distinct from the Reeves response role;
- no server-side prompt or history persistence;
- real request-byte limit, CORS allowlist and single-process rate limit;
- browser automatically falls back to the local 21-topic engine.

The browser also has a separate opt-in local memory: it is disabled by default,
bounded to 40 turns, visible to the user and deletable in one action. This is
not server persistence.

## Local run

```powershell
$env:REEVES_PROVIDER='mock'
$env:REEVES_ALLOWED_ORIGINS='http://127.0.0.1:8000'
python -m uvicorn reeves_api.app:app --host 127.0.0.1 --port 8787
```

Then set `apiEnabled: true` and `apiBaseUrl: 'http://127.0.0.1:8787'` in the
public, non-secret `assets/assistant-config.js` file used by the local preview.

## Production boundary

The in-memory limiter is suitable only for one beta process. Internet-facing
deployment needs a shared rate limiter, a daily token/cost budget, a circuit
breaker, secret-manager custody for the provider key, abuse monitoring that
does not log prompt bodies, and an explicit retention policy. The mock passing
tests does not validate a paid provider or production deployment.
