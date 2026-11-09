# Enable the Reeves OpenAI provider

This adds a server-side model provider to the ROZUM Assistant. It does not attach
the current ChatGPT conversation or transfer its personal memories. Reeves runs
as a separate API application and receives only the request history and public
ROZUM excerpts described below.

The repository default remains \`REEVES_PROVIDER=mock\`; the public Pages setting
also remains \`apiEnabled: false\`. This branch therefore does not turn on model
traffic by itself.

## Backend environment

On the backend host, configure:

- \`REEVES_PROVIDER=openai\`;
- \`OPENAI_API_KEY\` as a host-managed secret;
- \`OPENAI_MODEL\` with a model available to the API project;
- optionally \`REEVES_MAX_OUTPUT_TOKENS=500\` (the adapter caps this at 800);
- \`REEVES_ALLOWED_ORIGINS=https://kastorrivz-droid.github.io\`.

Keep the API key out of GitHub, Pages configuration, screenshots and browser
requests. Do not paste the key into this chat. The current implementation uses
the OpenAI Responses API from the backend with a bounded request timeout.

From the repository root, the service starts with:

\`\`\`sh
PYTHONPATH=src python -m uvicorn reeves_api.app:app --host 0.0.0.0 --port 8787
\`\`\`

Check \`/healthz\` for liveness and \`/readyz\` for the selected provider name.
Neither endpoint reveals credentials.

## Data sent for a model reply

The browser sends the current message and up to 12 recent conversation turns to
the Reeves API. The backend forwards the current message, at most eight recent
turns (each limited to 1,500 characters), and at most two relevant public
documents checked out from this repository. It does not write prompt history to
its own storage. The OpenAI request sets \`store: false\`; requests are still sent
to the configured provider for processing, so review the API project's data
controls before enabling the public service.

The checkbox for local memory controls browser storage only. It is not required
for a reply, and it does not prevent the current conversation context from being
sent when remote mode is enabled.

## Enable the website

After the backend is deployed over HTTPS and its shared rate limit, usage budget,
and privacy notice are reviewed, set the public, non-secret
\`assets/assistant-config.js\` values to:

\`\`\`js
apiEnabled: true,
apiBaseUrl: 'https://your-backend-host'
\`\`\`

Never put \`OPENAI_API_KEY\` in that file. If the backend is unavailable, the
browser returns to the local knowledge engine.

The current limiter is in-memory and per-process. It is suitable for a single
beta instance, not a public service with an unbounded model budget. Keep
\`apiEnabled\` false until a shared rate/cost control and a reviewed usage budget
are in place.
