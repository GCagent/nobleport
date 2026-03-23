# KUZO Domain → Edge → App Cutover Runbook

This runbook turns a verified domain TXT hash into a working production entrypoint by wiring DNS, edge routing, TLS, and KUZO backend health checks.

## 1) Inputs you must finalize first

Before editing DNS, define these values:

- `DOMAIN_ROOT`: apex domain, e.g. `kuzo.io`
- `APP_SUBDOMAIN` (optional): e.g. `app.kuzo.io` if you do not want apex hosting
- `EDGE_PROVIDER`: `vercel` or `vultr`
- `EDGE_TARGET`:
  - Vercel: `your-project.vercel.app`
  - Vultr: public IPv4 of your Gateway Brain node or reverse-proxy hostname
- `VERIFICATION_TXT`: ownership token/hash from registrar flow (example used below: `3b52ff521bb9cb24674b4e0a5738bdd94d7508b7`)

> DNS records are only useful once the target edge endpoint is live and can proxy to KUZO.

## 2) Atom dashboard DNS plan

### Pattern A: apex + www (`kuzo.io` and `www.kuzo.io`)

Use this when `kuzo.io` should be the primary user-facing origin.

1. Add ownership TXT record:
   - Type: `TXT`
   - Host/Name: `@`
   - Value: `3b52ff521bb9cb24674b4e0a5738bdd94d7508b7`
2. Point apex (`@`) to edge:
   - **Vultr path:** `A @ -> <gateway_brain_public_ip>`
   - **Vercel path:** use the provider-supported apex target (commonly an `A`/`ALIAS` integration path in registrar UI) and keep project domain bound in Vercel
3. Point `www` to apex:
   - Type: `CNAME`
   - Host/Name: `www`
   - Target: `kuzo.io`

### Pattern B: subdomain app (`app.kuzo.io`)

Use this when root domain is reserved for marketing/docs.

1. Keep ownership TXT at `@` as required by registrar/project verification.
2. Add app record:
   - Vultr: `A app -> <gateway_brain_public_ip>`
   - Vercel: `CNAME app -> your-project.vercel.app`
3. Optionally route `www` to root or to `app`, based on your public URL strategy.

## 3) Edge and app wiring checklist

The edge must terminate HTTPS and forward traffic to KUZO services.

### Required KUZO surfaces

- Web UI on `80/443` via reverse proxy or managed host
- API routes:
  - `/api/nav`
  - `/api/forensics`
- WebSocket endpoints consumed by KUZO client hooks

### TLS expectations

- **Vercel**: managed HTTPS certificates (auto-provisioned after domain binding)
- **Vultr**: terminate TLS on Caddy/Nginx with Let's Encrypt certificates

### Reverse proxy expectations (Vultr path)

- Port `80` redirects to `443`
- Port `443` proxies to app upstream(s)
- `Upgrade` + `Connection` headers are forwarded for WebSockets
- Health endpoint available (e.g., `/healthz`) for monitoring and synthetic checks

## 4) Post-change verification commands

After waiting for propagation (often 5–30 minutes):

```bash
# Verify ownership TXT

dig TXT kuzo.io +short

# Verify apex resolution (A/CNAME path depending on setup)

dig kuzo.io +short

# Verify HTTPS response and redirect behavior

curl -I https://kuzo.io

# Verify key API routes (replace with the chosen origin)

curl -i https://kuzo.io/api/nav
curl -i https://kuzo.io/api/forensics
```

Optional WebSocket smoke test (if you expose a ws path):

```bash
# Example with websocat
websocat -v wss://kuzo.io/<ws-endpoint>
```

## 5) Hardening baseline

- Place edge behind Cloudflare (or equivalent) for WAF, DDoS mitigation, and basic rate limiting
- Enforce HTTPS-only traffic and HSTS
- Restrict direct origin access where possible (allow only edge IP ranges)
- Add synthetic uptime checks against `/`, `/api/nav`, and `/api/forensics`
- Emit structured request logs for incident triage

## 6) NoblePort / Stephanie.ai control-plane integration

Treat KUZO as a first-class NoblePort app:

- Register KUZO origin in Mission Control launcher metadata
- Keep auth model aligned across apps (zkSBT/JWT policy and issuer trust)
- Keep API origin/CORS policy consistent to avoid fragmented session behavior
- If publishing mirrored content to IPFS later, update ENS `contenthash` mapping as part of release workflow

## 7) Copy/paste template for change tickets

```text
Domain: <kuzo.io>
Primary Origin: <https://kuzo.io OR https://app.kuzo.io>
Edge Provider: <Vercel|Vultr>
Edge Target: <your-project.vercel.app OR public IP/hostname>
DNS Records:
  - TXT @ = 3b52ff521bb9cb24674b4e0a5738bdd94d7508b7
  - A/CNAME (primary origin) = <target>
  - CNAME www = <kuzo.io or app.kuzo.io>
TLS: <Managed by Vercel OR Let's Encrypt on proxy>
Verification:
  - dig TXT <domain>
  - curl -I https://<primary-origin>
  - API checks: /api/nav, /api/forensics
Security:
  - WAF enabled
  - Rate limits enabled
  - Origin lock-down complete
```
