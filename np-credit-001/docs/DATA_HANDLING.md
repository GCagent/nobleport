# Data handling — DRAFT

No real consumer data permitted in this prototype.

Classification: consumer PII, credit report contents, dispute records and consent records are restricted; credentials are secrets. Never store restricted content in repository files, logs, test fixtures or public blockchain records.

Production prerequisites: verified OIDC, scoped access, RLS, encryption at rest and in transit, documented retention and deletion schedules, consent lifecycle, durable access auditing, backups and restore evidence, written incident response procedures, and counsel review.

Retention periods and breach-notification deadlines must be established by counsel and the security owner before production. No retention period is authorized by this draft.
