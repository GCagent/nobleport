# Stephanie Connected Bot Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a testable Stephanie Telegram bot on a clean branch from current main, preserve fail-closed human governance, connect the bot read-only to authenticated GCagent API health, and expose geometric-reasoning health from the existing engine.

**Architecture:** Keep Telegram/OpenAI/SQLite concerns in `bots/steph_bot.py`. Add an isolated `NoblePortClient` that probes the existing authenticated `/api/gcagent/schema` endpoint without mutating server state. Reuse `api.geometric_reasoning` directly for deterministic health checks. Production deployment, payments, token actions, permit approvals, contract signing, and custody remain human-gated.

**Tech Stack:** Python 3.12, python-telegram-bot 21-22, httpx 0.27+, Pydantic v2 geometric reasoning core, pytest, pytest-asyncio, GitHub Actions.

## Global Constraints

- Secrets are environment-only; no credentials in source.
- Telegram user access is default-deny through `TELEGRAM_ALLOWED_USER_IDS`.
- No subprocess or arbitrary shell execution from the bot.
- NoblePort API connection is read-only in this upgrade.
- Sensitive operational actions require explicit human approval and fail closed.
- Geometry is verified through confidence gates; held geometry never enters structured project memory.
- LIVE VERIFIED requires runtime evidence; passing CI alone is CODED / TESTED.

---

### Task 1: CI and failing connection tests

**Files:**
- Create: `.github/workflows/steph-upgrade.yml`
- Create: `tests/test_steph_bot_safety.py`
- Create: `tests/test_steph_bot_connection.py`

**Interfaces:**
- Consumes: `api.geometric_reasoning`
- Produces: failing tests for `BotSettings`, `NoblePortClient`, `geometry_health_check`, `/status`, and `/geometry`

- [x] Add Python 3.12 CI with compile, geometric tests, bot safety tests, and connection tests.
- [x] Add safety assertions for no shell execution, env-only secrets, fail-closed allowlist, and human-gated sensitive actions.
- [x] Add connection tests for authenticated GCagent probe and geometric reasoning health.
- [x] Run CI and capture the initial failure evidence.

### Task 2: Minimal connected bot implementation

**Files:**
- Create: `bots/steph_bot.py`
- Create: `requirements-steph-bot.txt`

**Interfaces:**
- Produces: `BotSettings.from_env()`, `NoblePortClient.status()`, `geometry_health_check()`, Telegram `/status`, `/geometry`, `/audit`, `/deploy`, text, voice, and photo handlers.

- [ ] Implement runtime settings loading with fail-closed operator allowlist.
- [ ] Implement read-only authenticated GCagent status probe.
- [ ] Implement deterministic geometric reasoning health check using current NoblePort engine.
- [ ] Port text, voice, vision, memory, audit, and human-gated deploy behavior from the staged bot.
- [ ] Register `/status` and `/geometry` commands.
- [ ] Run CI and require all targeted tests to pass.

### Task 3: Runtime evidence and integration handoff

**Files:**
- Create: `docs/STEPH_BOT_CONNECTED_RUNBOOK.md`

**Interfaces:**
- Consumes: `TELEGRAM_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, `OPENAI_API_KEY`, optional `NOBLEPORT_API_URL`, `NOBLEPORT_API_TOKEN`
- Produces: explicit evidence gates for external connection promotion.

- [ ] Document required environment variables and startup command.
- [ ] Define runtime checks for authorized/unauthorized Telegram users, text, voice transcription, TTS, vision, `/status`, `/geometry`, memory persistence, API authentication, and rollback.
- [ ] Keep deployment status at CODED / TESTED until those external checks are executed on the target host.
