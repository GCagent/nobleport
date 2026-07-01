# NoblePort Field Operations API

**Truth status: STAGED / PENDING ACCEPTANCE VERIFICATION**

This repository contains the NoblePort FastAPI foundation for construction field operations and workflow controls. It is a staging codebase, not a certified production platform and not an offering, payment, investment, or compliance system.

## What is implemented on this branch

- Authenticated GCagent field intake for voice-command processing.
- Transcript-gated task creation, structured audit events, and retry handling for failed n8n dispatches.
- Async PostgreSQL persistence for jobs, tasks, audit records, retries, and change orders.
- Serialized audit-hash-chain writes to protect record ordering under concurrent requests.
- Slack request signature verification.
- Change-order approval/rejection records and basic downloadable job-log/change-order PDFs.
- Operational request IDs, security headers, CORS/host controls, liveness, readiness, Docker, and CI checks.
- Canonical text project IDs, allowing live identifiers such as `NP-GLORIA-2026-001` to remain intact across the ledger.

## What is deliberately not production-certified

- Legacy investor, KYC, token, and portfolio routes are simulation-only and disabled in production mode.
- Payment, eSign, and financial control nodes remain staged pending their own reconciliation, security, and legal acceptance gates.
- A production frontend is not present in this repository.
- Shared bearer-token authentication is a staging control, not final role-based authorization.

## Runtime modes

| Mode | Intended use | Field-operations repository | Legacy investor/token routes |
|---|---|---|---|
| `development` | Local development | In-memory by default | Simulation only |
| `test` | Automated tests | In-memory | Simulation only |
| `staging` | Protected operational validation | Postgres required for durable records | Simulation only |
| `production` | Approved deployment only | Postgres required | Disabled |

`/health/live` confirms process availability. `/health/ready` is fail-closed and returns `503` until runtime configuration, database reachability, and persistent repository initialization are all demonstrated.

## Local staging run

```bash
cp .env.example .env
# Set unique values for POSTGRES_PASSWORD and GCAGENT_API_TOKENS.
docker compose up --build
curl http://127.0.0.1:8000/health/live
curl -i http://127.0.0.1:8000/health/ready
```

The compose stack binds the API to `127.0.0.1:8000` and keeps PostgreSQL inside the Docker network. Do not expose the staging stack publicly without an approved ingress, TLS, secrets, role-based authorization, and monitoring plan.

## Quality gate

The GitHub Actions workflow checks:

1. Ruff linting.
2. Python package compilation.
3. Health and repository-contract tests.
4. Container buildability.

## Promotion requirements

Promotion from staging requires retained evidence that:

- The exact commit passed CI.
- Database migration, restart persistence, retries, and audit-chain verification passed in staging.
- Secrets are managed outside source control and have rotation procedures.
- Authorization prevents cross-project access.
- Backup and restore are rehearsed.
- Three live Revenue Spine jobs reconcile from intake through closeout against source documents and financial controls.
- A named approver signs the staging acceptance record.

See [`docs/staged-optimization-acceptance.md`](docs/staged-optimization-acceptance.md) for the operating acceptance checklist.

## License

Proprietary. Internal and authorized use only.
