# CLAUDE.md — Noble Port Realty Platform

## Project Overview

Noble Port Realty is an institutional-grade tokenized real estate investment platform combining premium real estate assets with blockchain technology. It tokenizes over $4.4M in real estate holdings using Solana's Token 2022 standard, enabling fractional ownership with embedded SEC compliance mechanisms.

### Key Properties
- Miami waterfront condominium (residential)
- Austin office property (commercial)
- Denver land parcel (development)

### Core Innovation
Regulatory compliance is embedded directly into smart contracts, making compliance violations technically impossible rather than merely prohibited.

---

## Repository Structure

```
nobleport/
├── api/                              # Python FastAPI backend
│   └── main.py                       # REST API (properties, investors, transactions, compliance)
├── contracts/                        # Solana smart contracts (Rust/Anchor)
│   └── nbpt_token.rs                 # NBPT Token 2022 contract with compliance hooks
├── docs/
│   ├── overview.md                   # Comprehensive platform documentation (~47 KB)
│   └── technical-specs.md            # Technical specifications
├── reports/
│   └── weekly/                       # Weekly progress reports (Markdown + PDF)
├── README.md                         # Project README
└── CLAUDE.md                         # This file
```

---

## Technology Stack

| Layer              | Technology                  | Status              |
|--------------------|-----------------------------|---------------------|
| Frontend           | React 19 + Vite             | Documented, not in repo |
| Backend API        | Python FastAPI              | Reference impl in `api/main.py` |
| Database           | PostgreSQL + DocumentDB     | Documented; in-memory demo in code |
| Blockchain         | Solana Token 2022           | Reference impl in `contracts/nbpt_token.rs` |
| Smart Contracts    | Rust (Anchor framework)     | Reference impl |
| Payment            | USDC stablecoin             | Multi-chain (9 networks) |
| KYC/AML            | Third-party integration     | Documented |
| Legal Structure    | Delaware LLC + SEC 506(b)   | Documented |

---

## Development Commands

### Backend (FastAPI)
```bash
# Run development server
uvicorn api:app --reload    # Serves on port 8000
```

### Frontend (React + Vite) — when present
```bash
npm run dev                 # Dev server on port 3000
npm run build               # Production build
```

### Smart Contracts (Anchor) — when configured
```bash
anchor build                # Build Solana programs
anchor test                 # Run contract tests
anchor deploy               # Deploy to cluster
```

---

## API Endpoints Reference

### Health
- `GET /` — Health check

### Properties
- `GET /api/properties` — List properties (supports filters)
- `GET /api/properties/{id}` — Property details
- `POST /api/properties` — Create property (admin)

### Investors
- `POST /api/investors/register` — Register investor
- `GET /api/investors/{id}` — Investor details
- `POST /api/investors/{id}/kyc` — Submit KYC verification
- `POST /api/investors/{id}/investor-pass` — Issue soulbound Investor Pass

### Transactions
- `POST /api/transactions/purchase` — Purchase tokens
- `GET /api/transactions/{id}` — Transaction details
- `GET /api/investors/{id}/portfolio` — Investor portfolio

### Compliance & Utilities
- `GET /api/compliance/report` — Compliance audit report
- `GET /api/blockchain/networks` — Supported blockchain networks

---

## Smart Contract Functions (Solana)

| Function                          | Purpose                                    |
|-----------------------------------|--------------------------------------------|
| `initialize_token()`             | Initialize NBPT with compliance parameters |
| `issue_investor_pass()`          | Issue soulbound Investor Pass after KYC    |
| `transfer_with_compliance()`     | Transfer tokens with SEC compliance checks |
| `configure_confidential_transfer()` | Enable zero-knowledge proofs            |
| `revoke_investor_pass()`         | Revoke credentials for violations          |
| `pause_transfers()`              | Emergency circuit breaker                  |
| `unpause_transfers()`            | Resume transfers                           |

### Contract Error Codes
`NonAccreditedLimitReached`, `SenderNotVerified`, `RecipientNotVerified`, `LockupPeriodActive`, `BelowMinimumOwnership`, `TransfersPaused`, `Unauthorized`

---

## Data Models

### Core Entities (defined in `api/main.py`)
- **Property** — ID, name, type, location, tokenization details, LLC entity
- **Investor** — ID, email, wallet address, KYC status, accreditation status, Investor Pass
- **TokenTransaction** — property, buyer/seller, amount, price, blockchain network
- **Portfolio** — investor holdings, values, ownership percentages

---

## Compliance Architecture

### SEC Rule 506(b) Enforcement
- Automated non-accredited investor limit (max 35 per property)
- Unlimited accredited investors
- Pre-existing relationship requirements

### Transfer Controls (enforced at smart contract level)
- KYC verification check
- Accreditation status check
- Lockup period enforcement (Regulation D)
- Minimum ownership percentage maintenance
- Soulbound (non-transferable) Investor Pass tokens

### Risk Management
- Third-party smart contract audits
- Multi-signature wallets
- Circuit breakers (pause/unpause)
- Encrypted storage for sensitive data

---

## Conventions for AI Assistants

### Code Style
- **Python**: Follow PEP 8. Use Pydantic models for data validation. Use type hints on all function signatures.
- **Rust**: Follow standard Rust formatting (`rustfmt`). Use Anchor macros and patterns for Solana programs.
- **Frontend (React)**: Component-based architecture. Theme colors: golden amber (`#D4AF37`) + deep navy (`#1A1A2E`). Montserrat typography.

### Git Conventions
- Write descriptive commit messages explaining what was added or changed
- Keep commits focused on a single logical change

### Key Principles
1. **Compliance-first**: Never bypass or weaken regulatory enforcement mechanisms. Compliance is enforced at the smart contract level by design.
2. **Security**: Do not expose private keys, wallet secrets, or investor PII. Validate all external inputs.
3. **Legal structure**: Each property is held in a separate Delaware LLC. Respect this isolation in code.
4. **Multi-chain awareness**: The platform supports 9 blockchain networks (Ethereum, Solana, Arbitrum, Polygon, Avalanche, Cardano, BNB Chain, Optimism, Base). Code should remain chain-agnostic where possible.
5. **Minimum investment**: 25% ownership stake minimum. This is enforced in smart contracts — do not lower this without explicit instruction.

### What Not to Do
- Do not remove or weaken compliance checks in smart contracts or API
- Do not hardcode wallet addresses or private keys
- Do not bypass KYC/AML verification flows
- Do not modify the SEC 506(b) investor limits without legal review
- Do not add dependencies without justification

---

## Broader Platform Context

Noble Port Realty is part of a larger AI-powered construction and real estate operating system:

| Component         | Role                                      |
|-------------------|-------------------------------------------|
| **Stephanie.ai**  | Strategist agent — orchestration & planning |
| **Devin**         | Builder agent — autonomous engineering     |
| **GCagent.ai**    | Domain agent — contractor workflows        |
| **PermitStream.ai** | Domain agent — municipal permits & zoning |
| **Cyborg.ai**     | Domain agent — compliance & security       |
| **NoblePort**     | Tokenized real estate investment platform  |

This three-layer architecture (Strategist + Builder + Domain Agents) forms a self-improving AI flywheel where data from domain agents feeds back into strategic decisions.
