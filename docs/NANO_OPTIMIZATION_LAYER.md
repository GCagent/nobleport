# NoblePort Nano Optimization Layer

Status: **STAGED / CODED / NOT RUNTIME-VERIFIED**

The Nano Optimization Layer is a small execution-planning component intended to reduce context size and wall-clock latency without weakening NoblePort governance.

## What it does

- Routes requests into `FAST`, `STANDARD`, `REASONING`, or `GATED` lanes.
- Marks financial, custody, token-transfer, securities, permit-approval, contract-execution, and similar actions as fail-closed / human approval required.
- Preserves mandatory governance and evidence context even when the context budget is exceeded.
- Prunes lower-value context using relevance-per-character scoring.
- Runs independent **read** operations concurrently with isolated timeouts.
- Provides timing helpers for before/after benchmark instrumentation.
- Exposes an advisory FastAPI router at `/api/nano/*`.

## What it does not do

- It does not release funds.
- It does not transfer tokens or assets.
- It does not approve permits.
- It does not sign or execute contracts.
- It does not promote integrations to LIVE VERIFIED.
- It does not treat modeled savings as runtime evidence.

## FastAPI integration

Mount the router in the existing application:

```python
from .nano_router import router as nano_router

app.include_router(nano_router)
```

Endpoints:

- `GET /api/nano/health`
- `POST /api/nano/plan`

Example plan input:

```json
{
  "request": "summarize project status",
  "context": [
    {
      "key": "project",
      "text": "project record...",
      "relevance": 10,
      "mandatory": false,
      "evidence_class": "VERIFIED"
    },
    {
      "key": "governance",
      "text": "human approval policy...",
      "relevance": 5,
      "mandatory": true,
      "evidence_class": "VERIFIED"
    }
  ]
}
```

## Benchmark policy

Capture these metrics before and after deployment:

1. P50/P95 total workflow latency.
2. Time to first token for AI workflows.
3. Context characters/tokens supplied to the model.
4. RAG retrieval latency.
5. External connector latency by provider.
6. Evidence Ledger write latency.
7. Cost per completed workflow.
8. Human correction rate.

A reduction may be promoted from **MODELED** to **VERIFIED** only when reproducible runtime traces and the corresponding evidence record exist.

## Safety invariant

Latency optimization never overrides governance. Mandatory policy/evidence context is retained even if doing so exceeds the optimization budget, and irreversible writes must not be placed in the generic parallel-read helper.

## Test

```bash
python -m unittest tests.test_nano_optimizer -v
```

The code is intentionally dependency-light and uses the Python standard library for the optimization core.
