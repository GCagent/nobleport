# CLAUDE.md — Noble Port Realty

## Project Overview

Noble Port Realty is an institutional-grade tokenized real estate investment platform built on Solana's Token 2022 standard. It enables fractional ownership of premium properties ($4.4M+ portfolio across Miami, Austin, Denver) while embedding SEC Rule 506(b) compliance directly into smart contracts.

**Key concept:** Compliance-as-code — regulatory requirements are enforced at the protocol level, making violations technically impossible rather than merely prohibited.

## Repository Structure

```
nobleport/
├── CLAUDE.md               # This file
├── README.md               # Project overview, portfolio details, getting started
├── api/
│   └── main.py             # Python FastAPI backend (all endpoints, models, in-memory DB)
├── contracts/
│   └── nbpt_token.rs       # Solana smart contract (Rust/Anchor framework)
├── docs/
│   ├── overview.md          # Comprehensive platform documentation (47KB)
│   └── technical-specs.md   # Architecture summary
└── reports/
    └── weekly/
        └── weekly_progress_report_2025-12-08.md  # Operations report
```

**Note:** The README references additional files and directories (frontend/, models.py, blockchain.py, tests/) that do not yet exist in the repository. The current codebase consists of the API backend, one smart contract, and documentation.

## Languages and Frameworks

| Component | Language | Framework | File |
|-----------|----------|-----------|------|
| Backend API | Python | FastAPI + Pydantic | `api/main.py` |
| Smart Contract | Rust | Anchor (Solana) | `contracts/nbpt_token.rs` |
| Documentation | Markdown | — | `docs/`, `README.md` |

## Development Setup

```bash
# Backend API
pip install fastapi pydantic uvicorn
uvicorn api.main:app --reload  # Runs on port 8000

# Smart contract (requires Solana toolchain)
# Anchor framework for building/testing contracts
```

**No configuration files exist yet** — there is no `requirements.txt`, `Cargo.toml`, `package.json`, `.env.example`, or CI/CD pipeline in the repository.

## Architecture

### Backend API (`api/main.py`)

Single-file FastAPI application containing all models, endpoints, and business logic. Uses in-memory dictionaries for storage (production target: PostgreSQL + DocumentDB).

**API base path:** `/api/`

**Endpoint groups:**
- `GET /` — API info and feature list
- `/api/properties` — Property CRUD (list, get, create)
- `/api/investors` — Investor registration, KYC, Investor Pass issuance, portfolio
- `/api/transactions` — Token purchase and transaction lookup
- `/api/compliance/report` — Compliance reporting
- `/api/blockchain/networks` — Supported blockchain networks

**Data models (Pydantic):**
- `Property`, `PropertyType` — Real estate assets with type enum (residential, commercial, development, mixed_use)
- `Investor`, `InvestorStatus` — User accounts with status enum (pending, verified, accredited, rejected)
- `KYCVerification`, `KYCStatus` — Identity verification tracking
- `TokenTransaction`, `TransactionType`, `TransactionStatus` — Blockchain transactions
- `Portfolio` — Aggregated investor holdings

**Patterns used:**
- UUIDs for all resource identifiers
- `created_at` / `updated_at` ISO datetime timestamps on all models
- String enums (`str, Enum`) for all status fields
- `HTTPException` for error responses with appropriate status codes
- CORS middleware enabled (configured for `*` origins — needs production lockdown)

### Smart Contract (`contracts/nbpt_token.rs`)

Solana Token 2022 contract using Anchor framework. Implements SEC-compliant token transfers with embedded regulatory checks.

**Program functions:**
1. `initialize_token` — Set compliance parameters (max 35 non-accredited investors, lockup period, min ownership %)
2. `issue_investor_pass` — Mint soulbound (non-transferable) token after KYC verification
3. `transfer_with_compliance` — Transfer tokens with full compliance validation
4. `configure_confidential_transfers` — Enable zero-knowledge proof privacy
5. `pause_transfers` / `unpause_transfers` — Emergency circuit breaker
6. `revoke_investor_pass` — Deactivate an investor's access

**Account structures:**
- `TokenConfig` — Global token configuration and compliance state
- `InvestorPass` — Per-investor soulbound credential (KYC hash, accreditation status)

**Error codes:** `NonAccreditedLimitReached`, `SenderNotVerified`, `RecipientNotVerified`, `LockupPeriodActive`, `BelowMinimumOwnership`, `TransfersPaused`, `Unauthorized`

## Code Conventions

### Python (API)

- Single-file architecture with all logic in `api/main.py`
- Pydantic `BaseModel` for all request/response schemas
- `Field(default_factory=...)` for auto-generated UUIDs and timestamps
- RESTful URL patterns: `/api/{resource}` for collections, `/api/{resource}/{id}` for instances
- Nested resources for sub-operations: `/api/investors/{id}/kyc`, `/api/investors/{id}/portfolio`
- Error handling via `HTTPException(status_code=..., detail=...)`
- Type hints on all function signatures and model fields

### Rust (Smart Contract)

- Anchor framework macros: `#[program]`, `#[account]`, `#[derive(Accounts)]`
- Triple-slash `///` doc comments on all public functions
- `Result<()>` return type with custom `ErrorCode` enum
- `msg!()` macro for on-chain logging
- Context structs (`Context<T>`) for account validation
- Account constraints via Anchor's `#[account(...)]` attributes

### General

- UUIDs (v4) for all entity identifiers
- ISO 8601 datetime strings for timestamps
- Descriptive enum values in snake_case
- Documentation in Markdown format

## Domain Concepts

- **NBPT Token** — Noble Port Token, the platform's utility token (100M fixed supply, no inflation)
- **Investor Pass** — Soulbound (non-transferable) token issued after KYC, required for all platform interactions
- **SEC Rule 506(b)** — Private placement exemption limiting non-accredited investors to 35 per offering
- **Regulation D lockup** — Required holding period before tokens can be transferred
- **Token 2022** — Solana's extended token standard supporting transfer hooks, confidential transfers, and metadata
- **Compliance-as-code** — Regulatory rules enforced programmatically in smart contracts
- **Delaware LLC** — Each property operates through its own LLC for legal separation
- **USDC** — Stablecoin used for all transactions (1:1 USD peg)

## Multi-Chain Support

The platform targets 9 blockchain networks: Solana (primary), Ethereum, Arbitrum, Cardano, Polygon, Avalanche, BNB Chain, Optimism, Base. The API tracks network configurations in a `BLOCKCHAIN_NETWORKS` dictionary.

## What's Missing (Not Yet Implemented)

These are referenced in documentation but not present in the repo:

- **Frontend** — React 19 + Vite application (referenced in README)
- **Database layer** — PostgreSQL + DocumentDB (API uses in-memory dicts)
- **Test suites** — No Python tests, no Rust contract tests
- **Configuration files** — No `requirements.txt`, `Cargo.toml`, `package.json`, `.env.example`
- **CI/CD** — No GitHub Actions or other pipeline configuration
- **Docker** — No containerization setup
- **KYC/AML integration** — External service integration code not present

## Working with This Codebase

### When modifying the API (`api/main.py`):
- Follow existing Pydantic model patterns for new data structures
- Add new endpoints using FastAPI decorators with appropriate HTTP methods
- Maintain the RESTful URL convention under `/api/`
- Use `HTTPException` for all error responses
- Add new resources to the in-memory `*_db` dictionaries

### When modifying the smart contract (`contracts/nbpt_token.rs`):
- Follow Anchor framework patterns for new instructions
- Add corresponding `Context` structs for account validation
- Add error variants to the `ErrorCode` enum
- Document functions with `///` comments
- All transfer-related functions must check compliance state (paused, Investor Pass, lockup)

### When adding documentation:
- Place technical docs in `docs/`
- Use Markdown format consistent with existing files
- Keep README.md focused on project overview; put details in `docs/`

## License

Proprietary — Copyright 2025 Noble Port Realty. All rights reserved. Unauthorized use is prohibited.
