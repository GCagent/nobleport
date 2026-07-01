# NoblePort Staged Optimization Acceptance

## Purpose

This branch establishes a defensible staging baseline for the NoblePort API. It does **not** certify live payments, investor compliance, on-chain activity, e-signing, or construction financial controls.

## What is now controlled

- Explicit `development`, `test`, `staging`, and `production` runtime modes.
- No wildcard CORS in the default runtime configuration.
- Host validation, request correlation IDs, response security headers, and request timing.
- `/health/live` for process health and `/health/ready` for fail-closed dependency proof.
- Non-root container execution and a localhost-only Docker Compose API exposure.
- CI checks for linting, bytecode compilation, tests, and container buildability.
- Raw SSNs and identity document payloads removed from the staged KYC request contract.
- Legacy investor/token routes marked simulation-only and disabled in production.
- GCagent production requests blocked until an actual Postgres repository adapter replaces the in-memory repository.

## Current hard blockers

1. **GCagent persistence:** `api/gcagent.py` still uses `InMemoryGCRepository`; implement async Postgres reads/writes for jobs, tasks, audit records, retry queue, and change orders.
2. **Migration discipline:** run the migration through a versioned migration runner and prove rollback/restore against a clean database.
3. **Secrets:** place all API tokens, Slack secrets, n8n URLs, payment credentials, and signing keys in managed secrets storage; rotate any key that has appeared in local files or logs.
4. **Authentication and authorization:** replace single shared bearer tokens with user/service identities, roles, least privilege, and audit attribution.
5. **Workflow evidence:** prove HubSpot lead → Bid → Proposal/Contract → Build → Change Order → Invoice/AR → Closeout on three live jobs with source-document reconciliation.
6. **Payment and eSign:** keep payment and eSign nodes staged until their security, retention, legal, and reconciliation tests are independently passed.
7. **Frontend:** no runnable frontend package was present in this repository during this optimization pass. Do not treat the README architecture statement as verification of a production user interface.

## Verification sequence

```bash
cp .env.example .env
# Set unique local values for POSTGRES_PASSWORD and GCAGENT_API_TOKENS.
docker compose up --build
curl http://127.0.0.1:8000/health/live
curl -i http://127.0.0.1:8000/health/ready
```

Expected result: `/health/live` returns `200`; `/health/ready` returns `503` until the hard blockers are closed. That is the correct staged outcome.

## Promotion gate

Do not promote this branch until all of the following are demonstrated and retained as evidence:

- CI is green on the exact promotion commit.
- Database persistence survives a restart and an intentional retry cycle.
- Hash-chain audit verification passes against stored records.
- Authorization tests prove no cross-project access.
- Backup restore is rehearsed.
- Security review clears the exposed API surface.
- Three live Revenue Spine jobs reconcile to source documents and approved financial controls.
- A named approver signs the staging acceptance record.
