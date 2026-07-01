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
- Async Postgres persistence for GCagent jobs, tasks, audits, retries, and change orders.
- Transaction-serialized audit-chain writes, preventing concurrent audit events from splitting the hash chain.
- Canonical text project IDs are retained in the field-operations schema, including IDs such as `NP-GLORIA-2026-001`.

## Current hard blockers

1. **Persistence proof:** run the database migration against a clean staging database, prove jobs/tasks/change orders survive restart, and prove retry updates do not duplicate queue records.
2. **Migration discipline:** introduce a versioned migration runner and prove rollback/restore. The repository migration is suitable for a new staging database; do not apply a type-changing schema replacement to a populated environment without a reviewed migration plan.
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

Expected result in staging: `/health/live` returns `200`; `/health/ready` remains `503` until broader acceptance gates are complete. With `APP_ENV=production`, the legacy investor/token routes are disabled and readiness can become `200` only after valid configuration, database reachability, and the persistent GCagent repository are demonstrated.

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
