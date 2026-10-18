# ROZUM on Railway

**Status:** PRE-PRODUCTION DEPLOYMENT / NON-NORMATIVE

**Runtime:** ROZUM receiver 0.2.1

**Protocol baseline:** ROZUM_AI_v2.1 (unchanged)

This deployment keeps the current architecture deliberately small: one Python
receiver, one persistent SQLite replay store, and one replica in
`europe-west4`. It does not claim full `CVT-002 PASS` or production readiness.

## Security gates

Do not generate a public Railway domain until all of the following are true:

- both GitHub tokens previously pasted into chat have been revoked;
- `/data/config/key-registry.json` contains only approved production peers;
- no CVT/test private key or shared secret is reused;
- every HMAC value exists only in Railway Variables or another secret manager;
- `/readyz` is healthy and the volume backup policy is enabled;
- the endpoint is marked PRE-PRODUCTION while outbound protocol errors remain
  unsigned in runtime 0.2.1.

`config/key-registry.test.json` must never be used for an internet-facing
service.

## Repository layout

- `Dockerfile` builds the Python 3.12 receiver and drops privileges before
  starting it;
- `.railway/railway.ts` defines the GitHub source, one replica, healthcheck and
  1 GiB persistent volume;
- `config/key-registry.production.example.json` is a non-secret template;
- `/data/replay.sqlite3` is the authoritative persistent replay store;
- `/data/config/key-registry.json` is the operational trust registry.

The Railway definition intentionally creates no public domain.

## First deployment

Requirements: Node.js 22+, Railway CLI 5.42.1 or newer, a Railway account, and
GitHub App access to the private `kastorrivz-droid/rozum-os` repository.
`npm ci` installs the pinned IaC SDK 3.11.0. Install the current Railway CLI
separately from Railway's official installer; it is intentionally not included
as an npm dependency.

1. Create an empty Railway project named `rozum-os` with a `production`
   environment and select the Hobby plan.
2. From a trusted computer, install the pinned IaC dependency:

   ```bash
   npm ci
   ```

3. Authenticate and link the repository checkout:

   ```bash
   railway login
   railway link
   ```

4. Review the exact plan before applying it:

   ```bash
   npm run railway:plan
   npm run railway:apply
   ```

   The initial service can remain unready until the production registry and its
   referenced secrets exist. This is the intended fail-closed state.

5. On the trusted computer, copy the template outside Git tracking, replace the
   peer identity/profile with verified values, and upload it to the volume:

   ```bash
   cp config/key-registry.production.example.json /secure/path/key-registry.json
   railway volume files upload /secure/path/key-registry.json /config/key-registry.json
   ```

6. If the registry uses the included HMAC example, create the service variable
   `ROZUM_HMAC_TRUSTED_PEER_V1` in Railway with a fresh high-entropy secret. Do
   not paste the value into Git, an issue, build arguments, or deployment logs.
   For Ed25519, store only the peer's public key in the registry and keep the
   private key with the sender.
7. Restart the receiver and confirm `/readyz` returns HTTP 200. Then enable
   automated volume backups and perform a restore drill.
8. Only after the gates above pass, generate a Railway domain and run the live
   PRE-CVT-002 interoperability tests.

## Runtime variables

| Variable | Railway value | Secret |
|---|---|---:|
| `ROZUM_KEY_REGISTRY` | `/data/config/key-registry.json` | No |
| `ROZUM_POLICY` | `config/receiver-policy.v2.1.json` | No |
| `ROZUM_REPLAY_DB` | `/data/replay.sqlite3` | No |
| `ROZUM_RECEIVER_ID` | `argos_receiver` | No |
| `ROZUM_RECEIVER_KEY_ID` | `manual-errors-v1` | No |
| `ROZUM_HMAC_TRUSTED_PEER_V1` | fresh random value, if HMAC is selected | Yes |
| `PORT` | injected automatically by Railway | No |

The service must remain at one replica while SQLite is the authoritative replay
store. Horizontal scaling requires a shared production replay store and a new
load/crash test.

## Verification after every deploy

```bash
curl --fail https://YOUR_DOMAIN/healthz
curl --fail https://YOUR_DOMAIN/readyz
```

Then run the protocol fixtures from `runtime/CVT-002_CHECKLIST.md`, confirm the
expected `202/401/409/422` responses, inspect logs for secret leakage, and save
the receiver traces as test evidence.
