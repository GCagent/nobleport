# NoblePort Operational Telemetry — Honest Baseline

**Version:** 0.1
**Date:** 2026-03-02
**Classification:** Internal — pre-instrumentation working document
**Supersedes:** "NoblePort Full Optimization Report" dated 2026-01-19 (**withdrawn** — fabricated telemetry, hallucinated chain heights, AI-attributed authorship, no methodology)

---

## 0. Why this document exists

The prior optimization report could not survive your governance bundle. Block heights were two years stale; every metric carried 3-4 decimal places of false precision; industry benchmarks were uncited; financial savings figures had no baseline; the document was attributed to "Manus AI" overseen by "Stephanie.ai," which violates the standing accreditation rule.

This baseline replaces it. Rules:

1. **Every metric names its source instrument.** If no instrument exists, the metric is omitted and a `MEASUREMENT REQUIRED` row is added.
2. **No false precision.** Numbers are reported to the precision the underlying measurement supports.
3. **No "industry benchmarks" without a cited source** with date and methodology.
4. **No AI authorship attribution.** Authored by the operator. Tooling used is noted as tooling, not as overseer.
5. **No "Score / 100" composite metrics** without a published scoring rubric.

---

## 1. System Inventory & Tier

| System | Tier | Notes |
|---|---|---|
| Revenue Closure Engine (CF Workers / D1 / Hono) | **LIVE** | HubSpot + Stripe + PayPal webhooks instrumented |
| GCagent.ai lead pipeline | **LIVE** | PostgreSQL dedup, Twilio/SendGrid outreach |
| NoblePort Command Center (Replit) | **LIVE** | Roofing estimate / proposal pipeline |
| SnapshotRegistry.sol on Arbitrum One | **LIVE** | Canary: Andover, MA |
| KUZO Pro Terminal (Fly.io) | **LIVE** | JWT auth, Redis nonce, WebSocket hardened |
| Stephanie.ai canonical voice pipeline | **LIVE** | ElevenLabs → Redis → LangGraph → RAOS → policy gate → tool router → schema validation → AuditBeacon |
| HITL Approval Console | **STAGED** | Three-entity model; pending deployment |
| NBPT Settlement Loop (ERC-1400) | **STAGED** | Pre-audit (Trail of Bits scope defined) |
| NPETF tokenized real estate fund | **PLANNED** | Counsel-gated (Cooley) |
| Merkle anchoring to Arbitrum L2 Registry | **PLANNED** | Specified, not deployed |
| NVIDIA NIM / Riva / Audio2Face / Omniverse | **ARCHITECTURE** | Reference only — explicitly demoted from prior LIVE claims |
| BowOrders.sol (ERC-1155) | **LIVE on testnet** / **STAGED on mainnet** | Audit-pending |

---

## 2. Payment Systems — Instrumentation Status

| Platform | Connection | Production Use | Telemetry Source | Reportable Metrics |
|---|---|---|---|---|
| Stripe | Live keys configured | Yes (proposals, deposits) | Stripe Dashboard + webhook ledger | TPS, success rate — `MEASUREMENT REQUIRED` (need 30-day pull) |
| Mercury | Operating account live | Yes (banking) | Mercury statements | Settlement count, ACH volume — `MEASUREMENT REQUIRED` |
| PayPal | Live keys configured | Yes (alternative payment) | PayPal webhook ledger | `MEASUREMENT REQUIRED` |
| MetaMask | RPC connection only | **No production payment flow** | n/a | No metrics — prior report's "9.5 TPS" was fabricated |

**Action:** pull 30-day windows from Stripe, Mercury, and PayPal dashboards. Publish actual counts. Do not impute "TPS" until a sustained-load test is run.

---

## 3. Blockchain — Honest State

| Chain | Deployment | Live Contracts | Mainnet Activity |
|---|---|---|---|
| Arbitrum One | **LIVE** | SnapshotRegistry.sol (PermitStream) | Andover canary writes |
| Ethereum mainnet | **No NoblePort contract deployments at this time** | n/a | Wallet activity only (treasury) |
| Polygon | **No deployments** | n/a | n/a |
| BNB Chain | **No deployments** | n/a | n/a |

**Withdrawn from prior report:**

- "Ethereum batching savings $630.83/month" — no NoblePort Ethereum contract is deployed; no batching is occurring.
- "Polygon batching savings $118.95/month" — no Polygon deployment.
- "BNB batching savings $134.56/month" — no BNB deployment.
- "Arbitrum optimization 42.58%" — SnapshotRegistry's gas profile is not optimized via batching; it's optimized by being on L2.

Any gas-savings claim requires: (a) deployed contract address, (b) before/after transaction hash references, (c) baseline assumption disclosed.

---

## 4. API & WebSocket — Measurement Required

| Surface | Hosting | Real-Time Metrics Source | Status |
|---|---|---|---|
| Revenue Closure REST endpoints | Cloudflare Workers | CF Analytics + Logpush | **Available — pull required** |
| KUZO Pro Terminal WebSocket | Fly.io | Fly metrics endpoint + Prometheus | **Available — pull required** |
| GraphQL API | n/a | **No public GraphQL API currently exposed** | Prior report's "23 queries / 51 subscriptions" was fabricated |

Until CF Analytics and Fly metrics are exported and a sampling window is fixed, no RPS, latency, or cache hit-rate figures will be published.

---

## 5. Database — What Is Actually Running

| Store | Service | Purpose | Telemetry |
|---|---|---|---|
| PostgreSQL | Supabase project "Nobleport Systems" | GCagent lead pipeline, Stephanie state | **Project flagged auto-paused per recent inbox audit — restore required before measurement** |
| Redis | n/a in production today | Caching layer | **PLANNED** — no live Redis cluster owned by NoblePort to my knowledge |
| D1 | Cloudflare | Revenue Closure Engine state | CF D1 metrics — pull required |

**Withdrawn:** "Redis: 689 MB used, 97.28% hit rate, 15,198 OPS" — no production Redis instance is currently the source of those numbers.

**Action:** restore Supabase project from paused state, then measure.

---

## 6. CDN / Edge / Network

| Component | Vendor | Status | Reportable |
|---|---|---|---|
| Edge / CDN | Cloudflare | LIVE for all CF Workers domains | CF Analytics — pull required |
| Load balancer | Cloudflare (implicit) | LIVE | No separate L4/L7 balancer fleet to report |
| WAF | Cloudflare WAF (default ruleset) | LIVE | Rule version + block counts — pull required |

**Withdrawn:** "Edge Locations Active: 187" (Cloudflare's PoP count is Cloudflare's, not NoblePort's claim to make); "Bandwidth saved 742.11 GB/month $2,226 savings" (no baseline cited).

---

## 7. Security Posture — Re-statement

Self-graded "95.84/100" is withdrawn. SOC 2 Type II observation window is **PLANNED**, not started. Until a third-party assessor produces a report, NoblePort will describe its controls qualitatively, not score them.

Documented controls (qualitative, not scored):

- TLS termination at Cloudflare (TLS 1.3 default).
- Cloudflare WAF default ruleset enabled on production domains.
- HSM custody: **PLANNED.** Not yet in place. W-001 (`0xc59e66BB2b6E19699F82A72a1569821cb1711504`) currently combines treasury, deployment, DAO, and personal roles — known segregation-of-duties gap, documented for pre-audit disclosure.
- Multi-factor: enforced on operator accounts (Anthropic, Cloudflare, HubSpot, Mercury, Stripe).
- Audit logging: AuditBeacon design is **STAGED**, not LIVE in all systems.

---

## 8. Financial Impact — Withdrawn Pending Reconciliation

All cost-savings figures from the prior report are withdrawn:

- $77,008/year total savings — no baseline disclosed
- $26,712/year CDN savings — no measured origin offload
- $13,283/year gas savings — no production transaction volume to support it
- $53,816/year bandwidth savings — no measured baseline

Operating burn, margin, and Sharpe figures are tracked in v1.0.2 of the Compliance & Architecture Report and require Mercury reconciliation before republication.

---

## 9. Action Items to Enable Honest Metrics

| # | Action | Owner | Blocker |
|---|---|---|---|
| 1 | Pull 30-day Stripe / Mercury / PayPal volume and success rates | Operator | None |
| 2 | Pull Cloudflare Analytics 30-day window (RPS, latency p50/p95/p99, cache hit ratio) | Operator | None |
| 3 | Pull Fly.io Prometheus metrics for KUZO Pro Terminal | Operator | None |
| 4 | Restore auto-paused Supabase project, then capture PG metrics | Operator | Supabase admin access |
| 5 | Define composite "system health" rubric **before** publishing any score | Operator | None |
| 6 | Document baseline infrastructure spend (Cloudflare, Fly, Mercury fees, Stripe fees, Supabase, ElevenLabs, Replit) | Operator | None — bills are on file |
| 7 | Trail of Bits audit on NBPT Settlement Loop | Trail of Bits | Scheduled |
| 8 | Replace HSM-pending W-001 with multisig + role separation | Operator | None — operational task |

---

## 10. Authorship & Tooling

**Authored by:** Michael O'Rourke, Operator, NoblePort Systems LLC.

**Tooling used in drafting:** Claude (Anthropic). Claude is a drafting tool, not an overseer, not an auditor, and not a licensed party. Any factual claim in this document is the operator's claim, not Claude's.

**Not authored by:** Stephanie.ai (which produces operational outputs subject to licensed human review, not compliance documents). **Not authored by:** "Manus AI" (no such party has standing to attest to NoblePort operations).

---

## 11. Version History

| Version | Date | Change |
|---|---|---|
| (prior) "Full Optimization Report" | 2026-01-19 | **Withdrawn.** Fabricated telemetry, stale chain heights, AI-attributed authorship, no methodology, self-graded scores, financial savings without baseline. |
| 0.1 | 2026-03-02 | Honest baseline. Names instruments. Lists what is unmeasured. No false precision. |

---

*End of document. To be re-issued as v0.2 once Action Items 1–4 produce measurable values.*
