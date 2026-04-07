# CLAUDE.md — Noble Port Realty

## Project Overview

Noble Port Realty is an institutional-grade tokenized real estate platform that uses Solana's Token 2022 standard to embed SEC compliance directly into smart contracts. The platform tokenizes premium real estate assets ($4.4M+ portfolio) and enables fractional ownership with automated regulatory enforcement.

The platform is part of the NoblePort Systems ecosystem, integrating with Stephanie.ai for AI-driven optimization and the NoblePort Operations Monitor.

## Repository Structure

```
nobleport/
├── api/
│   └── main.py              # Python FastAPI backend (all endpoints, models, enums)
├── contracts/
│   └── nbpt_token.rs        # Solana smart contract (Rust/Anchor, Token 2022)
├── docs/
│   ├── overview.md           # Comprehensive platform documentation
│   └── technical-specs.md    # Technical architecture specs
├── reports/
│   └── weekly/               # Weekly progress reports (md + pdf)
├── README.md                 # Project README with setup instructions
└── CLAUDE.md                 # This file
```

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend API** | Python 3, FastAPI, Pydantic, uvicorn | Single-file API at `api/main.py` |
| **Smart Contracts** | Rust, Anchor framework, Solana Token 2022 | Single contract at `contracts/nbpt_token.rs` |
| **Frontend** (planned) | React 19, Vite | Not yet in repo |
| **Database** (planned) | PostgreSQL + DocumentDB | Currently uses in-memory dicts |
| **Payments** | USDC stablecoin | Multi-chain (9 networks) |

## Key Architecture Concepts

### API (`api/main.py`)

The backend is a single FastAPI application with in-memory storage (dicts). All models, enums, and endpoints are in one file.

**Data Models:**
- `Property` — Tokenized real estate asset with LLC entity, token info, pricing
- `Investor` — User with KYC status, wallet address, Investor Pass state
- `KYCVerification` — Identity documents for verification
- `TokenTransaction` — Token purchase records with blockchain network
- `Portfolio` — Computed holdings for an investor

**Enums:** `PropertyType`, `InvestorStatus`, `TransactionStatus`, `BlockchainNetwork`

**Endpoint groups:**
- `GET/POST /api/properties` — Property CRUD
- `POST /api/investors/register` — Investor registration
- `POST /api/investors/{id}/kyc` — KYC submission
- `POST /api/investors/{id}/investor-pass` — Soulbound token issuance
- `POST /api/transactions/purchase` — Token purchase with compliance checks
- `GET /api/investors/{id}/portfolio` — Portfolio calculation
- `GET /api/compliance/report` — Regulatory compliance report
- `GET /api/blockchain/networks` — Supported chains list

**Important:** The API currently uses in-memory storage (`properties_db`, `investors_db`, `transactions_db` dicts). Production will use PostgreSQL + DocumentDB.

### Smart Contract (`contracts/nbpt_token.rs`)

Solana program using Anchor framework with Token 2022 extensions.

**Instructions:**
- `initialize_token` — Set up NBPT token with compliance params (max non-accredited investors, lockup period, min ownership %)
- `issue_investor_pass` — Mint soulbound KYC-verified credential to wallet
- `transfer_with_compliance` — Token transfer with full compliance checks (active Investor Pass, lockup period, min ownership, non-accredited limit)
- `configure_confidential_transfer` — Toggle zero-knowledge proof privacy
- `revoke_investor_pass` — Deactivate an investor's credential
- `pause_transfers` / `unpause_transfers` — Circuit breaker for emergencies

**Account structures:**
- `TokenConfig` — Global config (authority, investor limits, lockup, supply, pause state)
- `InvestorPass` — Per-investor soulbound credential (owner, accredited status, KYC hash, active flag)

**PDA seeds:** Investor Pass uses `[b"investor_pass", investor_pubkey]`

## Compliance Rules (Critical Domain Knowledge)

These rules are **core to the platform** and must never be violated in code changes:

1. **SEC Rule 506(b):** Maximum 35 non-accredited investors per property offering
2. **Soulbound Investor Pass:** Non-transferable; required for all token interactions
3. **KYC verification:** Must complete before receiving Investor Pass
4. **Lockup periods:** Regulation D requires holding periods before transfer
5. **Minimum ownership:** Transfers cannot reduce holdings below minimum % (unless selling all)
6. **Circuit breaker:** Authority can pause/unpause all transfers

## Development Workflow

### Running the API

```bash
pip install fastapi uvicorn pydantic[email]
uvicorn api.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs` (Swagger UI).

### Smart Contract Development

The Rust contract uses the Anchor framework targeting Solana. Build with:

```bash
anchor build
anchor test
anchor deploy
```

### Git Conventions

- **Main branch:** `master`
- **Commit messages:** Descriptive, prefixed with action (e.g., "Add ...", "Fix ...", "Update ...")
- **Author:** GCagent
- Single commits per logical change

## Important Notes for AI Assistants

1. **This is a proprietary codebase.** All rights reserved. Do not suggest open-sourcing or publishing code publicly.
2. **Compliance is non-negotiable.** Any code changes must preserve SEC 506(b) limits, KYC requirements, lockup enforcement, and minimum ownership checks. Never remove or weaken compliance logic.
3. **The API uses in-memory storage.** When adding features, use the existing dict-based storage pattern (`properties_db`, `investors_db`, `transactions_db`). Database migration is a separate future effort.
4. **The smart contract is a single file.** Keep `nbpt_token.rs` self-contained. All account structs, context structs, instructions, and error codes live in one file.
5. **CORS is permissive.** `allow_origins=["*"]` is set for development. Flag this if production deployment is discussed.
6. **Multi-chain support:** The platform supports 9 blockchain networks (Solana, Ethereum, Arbitrum, Polygon, Avalanche, Cardano, BNB Chain, Optimism, Base). The `BlockchainNetwork` enum must stay in sync with supported networks.
7. **NBPT token supply is fixed:** 100,000,000 tokens, no inflation. Never modify total supply logic.
8. **Frontend not yet implemented.** The README references React 19 + Vite but no frontend code exists in the repo yet. Design: golden amber (#D4AF37) and deep navy (#1A1A2E) theme with Montserrat typography.
9. **Reports directory** contains operational weekly reports (markdown + PDF). These are informational records, not code.
10. **Ecosystem context:** Noble Port Realty integrates with Stephanie.ai and the NoblePort Operations Monitor. Keep these integrations in mind for future work.
