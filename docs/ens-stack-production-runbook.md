# NoblePort ENS Stack Production Runbook

This runbook is for bringing up the ENS stack in production **after** the deployment archive is present.

## 1) Confirm the deployment archive exists

Do not continue until `nobleport-ens-stack.tar.gz` is actually available on the host:

```bash
cd /root
test -f nobleport-ens-stack.tar.gz
```

If the file is missing, stop and upload the archive first.

## 2) Unpack and inspect files

```bash
cd /root
tar -xzf nobleport-ens-stack.tar.gz
cd nobleport-ens-stack
find . -maxdepth 2 -type f | sort
```

## 3) Validate compose and environment files before boot

```bash
test -f docker-compose.yml -o -f compose.yaml
test -f .env.example -o -f .env
docker compose config
```

## 4) Configure production environment

```env
MAINNET_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
ENS_PRIVATE_KEY=YOUR_PRIVATE_KEY
ENS_NAME=nobleport.eth

GITHUB_WEBHOOK_SECRET=supersecurekey
PUBLIC_BASE_URL=https://api.nobleport.eth

PORT=8000
ENV=production
LOG_LEVEL=INFO
```

## 5) Build and run

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=200
```

## 6) Health checks

```bash
curl -i http://localhost:8000/
curl -i http://localhost:8000/health
```

Expect at minimum:
- `200 OK`
- app version
- runtime environment
- chain/RPC connectivity state (if implemented)

## 7) GitHub webhook signature test

Always compute the signature over the exact request body:

```bash
BODY='{}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac 'supersecurekey' | awk '{print $2}')
curl -i -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -d "$BODY"
```

## 8) ENS write verification flow

Do not run ENS writes blind. Before updating records, verify:
- signer wallet is funded
- chain/network matches intent
- resolver contract and ABI are correct
- you have a readback verification plan

Run write then immediate readback:

```bash
docker compose exec api python -c "from api.ens_service import update_core_records; print(update_core_records())"
docker compose exec api python -c "from api.ens_service import read_core_records; print(read_core_records())"
```

## 9) ENS vs DNS clarification

For `api.nobleport.eth`, do not assume classic DNS A-record handling unless you are intentionally using an ENS gateway/bridge pattern. In normal ENS operation, update the ENS resolver records through your ENS write flow.

## 10) Production hardening baseline

Do not expose raw `:8000` publicly. Place the app behind a reverse proxy and terminate TLS there.

Example NGINX HTTP proxy block:

```nginx
server {
    listen 80;
    server_name api.nobleport.eth;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then add TLS and enforce:
- webhook route restrictions (IP allowlist and/or auth checks)
- structured logging and alerting
- restart policies
- ENS write success/failure logging
- uptime monitoring
