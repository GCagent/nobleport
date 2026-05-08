# GCagent v1 production-hardening plan

GCagent v1 is organized as:

```text
FastAPI -> Postgres audit log -> TaskRouter -> Slack/n8n/PDF/ClientNotifier
```

Hard rule enforced by the API:

```text
No transcript, no task. No task, no audit log. No audit log, no field action.
```

## Implemented module coverage

- `SupervisorAgent`: API router coordinates intake, classification, audit logging, dispatch, and retries.
- `JobsiteAssistant`: default voice-log routing for field updates.
- `ChangeOrderHandler`: change-order creation, approval/rejection, audit trail, and PDF output.
- `TaskRouter`: deterministic category-to-agent routing from transcript content.
- `TaskAuditLogger`: append-only hash-chained audit entries.
- `Slack Inspection Bot` / `Slack Status Commands`: Slack event ingress with signature verification.
- `Retry queue`: failed n8n calls are blocked and queued for replay.
- `PDF Generator`: minimal PDF reports for job logs and change orders.

## Deployment notes

1. Apply `db/migrations/001_gcagent_core.sql` to the production Postgres database.
2. Configure `GCAGENT_API_TOKENS`, `N8N_WEBHOOK_URL`, and `SLACK_SIGNING_SECRET` from a secret manager.
3. Keep local `.env` files untracked; use `.env.example` only as a template.
4. Run the API with `uvicorn api.main:app --host 0.0.0.0 --port 8000`.
