# ML-DSA Implementation Details (FIPS 204)

## Status

ML-DSA (Module-Lattice-Based Digital Signature Algorithm) is standardized by NIST in FIPS 204 (published August 2024, with errata updates). It is the primary post-quantum signature scheme in this stack and is used in hybrid mode alongside ECDSA during migration.

## Cryptographic Basis

ML-DSA security relies on the hardness of the Module Learning With Errors (MLWE) and Module Short Integer Solution (MSIS) problems over module lattices.

Core ring/domain parameters:

- Modulus `q = 8380417`
- Polynomial degree `n = 256`
- Ring: `Z_q[X] / (X^256 + 1)`
- Public-key compression parameter `d = 13`

## Algorithm Flow (Fiat-Shamir with Aborts)

### 1) Key Generation

- Sample small secret vectors `s1`, `s2` with coefficients bounded by `eta`.
- Sample/publicly derive matrix `A` over the ring.
- Compute `t = A*s1 + s2`.
- Public key includes matrix seed + compressed `t`.
- Private key stores seeds and secret vectors (or equivalent expanded form).

### 2) Signing (Probabilistic)

- Sample masking vector `y` with coefficients bounded by `gamma1`.
- Compute commitment `w = A*y`.
- Derive sparse challenge polynomial `c` from message representative + high bits of `w`.
- Compute `z = y + c*s1`.
- Apply rejection sampling and hint generation/compression `h`.
- Restart if bounds/checks fail.

### 3) Verification (Deterministic)

- Recompute `w' = A*z - c*t`.
- Verify coefficient bounds on `z` and challenge consistency.
- Validate hint usage (`h`).

## Parameter Sets (FIPS 204)

| Variant | NIST Category | Public Key | Secret Key (expanded) | Signature |
|---|---:|---:|---:|---:|
| ML-DSA-44 | 2 | 1,312 B | 2,560 B | 2,420 B |
| ML-DSA-65 | 3 | 1,952 B | 4,032 B | 3,309 B |
| ML-DSA-87 | 5 | 2,592 B | 4,896 B | 4,627 B |

Implementation note: ML-DSA-65 is the default profile used here for a balanced security/performance tradeoff.

## Important Per-Variant Parameters

- Matrix dimensions `(k, l)`: `(4,4)`, `(6,5)`, `(8,7)`
- Challenge weight `tau`: `39`, `49`, `60`
- Secret bound `eta`: `2`, `4`, `2`
- Masking bound `gamma1`: `2^17`, `2^19`, `2^19`
- Rounding bound `gamma2`: `(q-1)/88`, `(q-1)/32`, `(q-1)/32`
- Rejection threshold `beta = tau * eta`: `78`, `196`, `120`
- Hint weight cap `omega`: `80`, `55`, `75`

## Implementation Guidance

### Library

Use liboqs for production integration where possible:

- Maintained post-quantum primitives
- Optimized backends (including AVX2 builds)
- Constant-time implementations for sensitive paths

### Build Guidance

```bash
cmake -DOQS_USE_AVX2_INSTRUCTIONS=ON -DCMAKE_BUILD_TYPE=Release ..
make
```

### Integration Policy (Hybrid Signatures)

For transition periods, sign and verify using both ECDSA and ML-DSA-65:

- **OR policy:** compatibility-first migration
- **AND policy:** stronger assurance, stricter acceptance

Store classical and PQC material side-by-side and make policy explicit at verification boundaries.

## Security Considerations

- Use constant-time implementations in all secret-dependent code paths.
- Use a strong CSPRNG/DRBG.
- Keep side-channel hardening enabled in release builds.
- Prefer hybrid mode during migration windows.

## Operations Checklist

- Confirm ML-DSA-65 key/signature sizes in wrappers and schemas:
  - Public key: `1952` bytes
  - Signature: `3309` bytes
- Run keygen/sign/verify tests for both standalone and hybrid flows.
- Validate deep health checks expose active PQC mode.
