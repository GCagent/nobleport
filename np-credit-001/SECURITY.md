# NP-CREDIT-001 — Security Policy (v0.3 draft)

**Status: DRAFT — not reviewed or approved. No production deployment authorized.**
**Scope:** NP-CREDIT-001 credit prototype.
**Companion documents:** DATA_HANDLING.md, COMPLIANCE.md, .gitignore.

## 1. Threat model

### Assets
Consumer PII (name, DOB, SSN, addresses, contact details); credit reports, tradelines, inquiries, scores and account numbers; disputes; versioned consent; OIDC, database and API credentials.

### Threat actors
External attackers (credential theft, upload injection, SSRF, supply-chain compromise); cross-tenant attackers; malicious or compromised insiders; upstream data-provider compromise. LLM prompt injection is out of scope until LLM features are designed and separately reviewed.

### Trust boundaries
- Internet → API: No live mutating consumer endpoints until verified OIDC and authorization. Flags OFF; submission hard-blocked.
- API → PostgreSQL: RLS is the mandatory tenant-isolation enforcement point, with application checks as defense in depth.
- API → bureaus/furnishers: No automated submission. Future submissions require an enabled flag, current scope-specific consent, human approval and a durable audit event, plus legal authorization.

## 2. Prohibited practices
1. Never log SSNs, full account numbers or DOBs; use opaque references.
2. Never commit credentials or secrets. Use an approved secrets manager.
3. Never ingest or submit without all required legal, identity, consent, approval and audit gates.
4. Never use production consumer data in development, tests or staging.
5. Never bypass consent gates for testing with real data.

## 3. Repository hygiene
- Ignore .env*, *.pem, *.key, *_rsa*, uploads/, *.zip, *.db and *.sqlite*.
- Secret scanning must block merges on findings.
- Use pull requests and at least one human reviewer; no force-push to main.
- Pin dependencies; block high/critical dependency findings pending documented review.
- Merge only tested, reviewed changes and record an artifact identifier.

## 4. Pre-production security gate
- [ ] OIDC identity and authorization on every consumer endpoint.
- [ ] PostgreSQL RLS on every consumer table; two-tenant integration test evidence attached.
- [ ] Feature flags OFF by default; enabled changes audited.
- [ ] Current, unrevoked, versioned consent for each exact use.
- [ ] Durable tamper-evident AuditBeacon events for every consumer-data read/write and gate decision.
- [ ] TLS 1.2+ in transit and AES-256 at rest for database and backups.
- [ ] Documented backup restore drill within 90 days.
- [ ] Written incident response plan and current contacts.
- [ ] Independent security review and remediation/risk acceptance.
- [ ] Written federal and Massachusetts legal approval.

## 5. Incident response
On suspected exposure, contain and revoke affected credentials, preserve evidence, determine scope and follow applicable notification obligations. Escalate uncertain cases.

## 6. Limitations
This policy is not a certification, legal opinion or authorization for production. A control counts as implemented only after independent test evidence.
