# CLAUDE.md - Noble Port Realty

## Project Overview

Noble Port Realty is an institutional-grade tokenized real estate platform that combines premium real estate assets with blockchain technology. It uses Solana's Token 2022 standard to embed SEC compliance (Rule 506(b)) directly into smart contracts. The platform tokenizes $4.4M+ in premium properties across Miami (residential), Austin (commercial), and Denver (development land).

**Key concept:** Regulatory compliance is cryptographically enforced at the protocol level — violations are technically impossible, not just prohibited.

## Repository Structure

```
nobleport/
├── CLAUDE.md              # This file — AI assistant guide
├── README.md              # Project overview, investor/developer docs
├── api/
│   └── main.py            # Python FastAPI backend (all endpoints, models, in-memory storage)
├── contracts/
│   └── nbpt_token.rs      # Solana smart contract (Rust/Anchor) — NBPT token with compliance
├── docs/
│   ├── overview.md         # Comprehensive platform documentation (~300 lines)
│   └── technical-specs.md  # Technical architecture specifications
└── reports/
    └── weekly/
        └── weekly_progress_report_2025-12-08.md  # Weekly operations report (+ PDF version)
```

## Tech Stack

| Layer       | Technology                        | Details                                              |
|-------------|-----------------------------------|------------------------------------------------------|
| Backend API | Python 3 + FastAPI                | RESTful API, Pydantic models, in-memory storage      |
| Smart Contract | Rust + Anchor framework        | Solana Token 2022 standard, compliance enforcement   |
| Frontend    | React 19 + Vite (planned)         | Not yet implemented in repo                          |
| Database    | PostgreSQL + DocumentDB (planned) | Currently uses in-memory dicts in `api/main.py`      |
| Blockchain  | Solana (primary), 9 chains total  | Multi-chain USDC support                             |
| Payments    | USDC stablecoin                   | Across Ethereum, Solana, Arbitrum, Polygon, etc.     |

## Key Components

### API Backend (`api/main.py`)

The FastAPI application is a single-file implementation with:

- **Enums:** `PropertyType`, `InvestorStatus`, `TransactionStatus`, `BlockchainNetwork`
- **Data models (Pydantic):** `Property`, `Investor`, `KYCVerification`, `TokenTransaction`, `Portfolio`
- **Storage:** In-memory dicts (`properties_db`, `investors_db`, `transactions_db`) — not production-ready
- **CORS:** Wide-open (`allow_origins=["*"]`) — must be restricted for production

**API endpoints:**
- `GET /` — Health check
- `GET/POST /api/properties` — List/create properties
- `GET /api/properties/{id}` — Property details
- `POST /api/investors/register` — Register investor
- `GET /api/investors/{id}` — Investor details
- `POST /api/investors/{id}/kyc` — Submit KYC verification
- `POST /api/investors/{id}/investor-pass` — Issue soulbound Investor Pass
- `POST /api/transactions/purchase` — Purchase property tokens
- `GET /api/transactions/{id}` — Transaction details
- `GET /api/investors/{id}/portfolio` — Investor portfolio
- `GET /api/compliance/report` — Compliance audit report
- `GET /api/blockchain/networks` — Supported blockchain networks

**Run the API:**
```bash
pip install fastapi uvicorn pydantic[email]
uvicorn api.main:app --reload --port 8000
```

### Smart Contract (`contracts/nbpt_token.rs`)

Solana program using the Anchor framework implementing the NBPT token:

- **`initialize_token`** — Sets up token config (max non-accredited investors, lockup period, min ownership %)
- **`issue_investor_pass`** — Mints soulbound (non-transferable) KYC credential token
- **`transfer_with_compliance`** — Token transfer with full compliance checks:
  - Both parties must have active Investor Pass
  - Lockup period enforcement (Regulation D)
  - Minimum ownership percentage enforcement
  - Non-accredited investor count limit (SEC Rule 506(b), max 35)
- **`configure_confidential_transfer`** — Enable/disable zero-knowledge proof privacy
- **`revoke_investor_pass`** — Revoke investor credentials (authority only)
- **`pause_transfers` / `unpause_transfers`** — Circuit breaker (authority only)

**Key account structures:**
- `TokenConfig` — Global config: authority, investor limits, lockup period, pause state
- `InvestorPass` — Per-investor: owner, accreditation status, KYC hash, soulbound flag

**Error codes:** `NonAccreditedLimitReached`, `SenderNotVerified`, `RecipientNotVerified`, `LockupPeriodActive`, `BelowMinimumOwnership`, `TransfersPaused`, `Unauthorized`

## Development Workflow

### Current State

This is an early-stage project. Key observations:

1. **No dependency files** — No `requirements.txt`, `package.json`, or `Cargo.toml` exists yet
2. **No tests** — No test files or test infrastructure
3. **No CI/CD** — No GitHub Actions, Dockerfile, or build scripts
4. **No `.gitignore`** — Missing; should be added
5. **In-memory storage** — The API uses Python dicts, not a real database
6. **Single-file API** — All models, routes, and storage live in `api/main.py`

### Branch Strategy

- `master` — Main branch
- Feature branches as needed

### Running Locally

**API server:**
```bash
# Install Python dependencies (no requirements.txt yet — install manually)
pip install fastapi uvicorn pydantic[email]

# Start the server
cd nobleport
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# API docs available at http://localhost:8000/docs (Swagger UI)
```

**Smart contract (requires Solana toolchain):**
```bash
# Install Anchor CLI and Solana CLI
# Build the contract
anchor build

# Deploy to devnet
anchor deploy --provider.cluster devnet
```

## Conventions and Guidelines

### Code Style

- **Python:** Follow PEP 8. Use type hints. Use Pydantic `BaseModel` for data validation.
- **Rust:** Follow standard Rust formatting (`rustfmt`). Use Anchor framework patterns for Solana programs.

### Naming

- **API routes:** RESTful, prefixed with `/api/`. Use kebab-case for multi-word paths (e.g., `/investor-pass`).
- **Python:** Snake_case for variables, functions, modules. PascalCase for classes and Pydantic models.
- **Rust:** Snake_case for functions and variables. PascalCase for types and structs. SCREAMING_SNAKE_CASE for constants.

### Domain-Specific Terminology

| Term | Meaning |
|------|---------|
| NBPT | Noble Port Token — the platform's utility token (100M fixed supply) |
| Investor Pass | Soulbound (non-transferable) KYC verification token |
| Transfer Hook | Solana Token 2022 mechanism for compliance checks on every transfer |
| Lockup Period | Regulation D holding period before tokens can be transferred |
| 506(b) Limit | SEC rule: max 35 non-accredited investors per property offering |
| Confidential Transfer | Zero-knowledge proof-based private transfers |
| Circuit Breaker | Emergency pause functionality for all token transfers |

### Security Considerations

- **Never expose** KYC personal data on-chain; only store verification hashes
- **Always validate** Investor Pass status before any token operation
- **Authority checks** are required for admin operations (pause, revoke, configure)
- **CORS** must be restricted to specific origins before production deployment
- **Input validation** — rely on Pydantic models for API input validation
- Smart contracts must be audited before mainnet deployment

### Architecture Decisions

- **API-first design** — Backend serves both the frontend and potential institutional integrations
- **Single-purpose LLCs** — Each property is a separate Delaware LLC for legal isolation
- **Multi-chain strategy** — 9 blockchain networks for flexibility and risk mitigation
- **USDC payments** — Stablecoin eliminates crypto volatility for real estate transactions
- **Soulbound tokens** — Non-transferable Investor Pass prevents credential sharing

## What Needs Work

Priority areas for development:

1. **Add dependency management** — Create `requirements.txt` for Python, `Cargo.toml` for Rust
2. **Add `.gitignore`** — Ignore `__pycache__`, `.env`, `target/`, `node_modules/`, etc.
3. **Split `api/main.py`** — Separate into models, routes, services, and database modules
4. **Add database layer** — Replace in-memory dicts with PostgreSQL/SQLAlchemy
5. **Add authentication/authorization** — The API currently has no auth; admin routes are unprotected
6. **Add tests** — Unit tests for API endpoints, integration tests for smart contract
7. **Restrict CORS** — Replace `allow_origins=["*"]` with specific allowed origins
8. **Add environment config** — Create `.env.example` with required environment variables
9. **Frontend implementation** — React 19 + Vite app (mentioned in README but not present)
10. **CI/CD pipeline** — GitHub Actions for linting, testing, and deployment

## Useful Commands

```bash
# Check API health
curl http://localhost:8000/

# View auto-generated API docs
open http://localhost:8000/docs

# List supported blockchain networks
curl http://localhost:8000/api/blockchain/networks

# Get compliance report
curl http://localhost:8000/api/compliance/report
```

## License

Copyright 2025 Noble Port Realty. All rights reserved. Proprietary — unauthorized use is prohibited.
