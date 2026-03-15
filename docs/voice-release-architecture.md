# Stephanie.ai Voice-Driven Release Architecture

This document defines a safe production release flow for voice-triggered mobile deployments.

## Control Flow

1. User issues a voice command (for example, "Stephanie, release Berns production build").
2. Speech recognition resolves command text and extracts intent payload.
3. Stephanie orchestrator sends normalized intent to the backend release gate API.
4. Release gate validates governance and safety checks.
5. When checks pass, the release gate authorizes the production EAS workflow.
6. CI workflow builds Android/iOS artifacts, submits to stores, and optionally runs OTA update.

## Release Gate Contract

Endpoint: `POST /api/release-gate`

Required checks:

- `intent` must be `release_app`
- `environment` must be `production`
- authorized requester (`RELEASE_ALLOWED_USERS` allowlist)
- valid admin signature (`RELEASE_ADMIN_SIGNATURE`)
- CI tests passing
- semantic version bump completed
- explicit second confirmation

### Example Request

```json
{
  "intent": "release_app",
  "app": "berns",
  "environment": "production",
  "requested_by": "Michael",
  "ci_tests_passing": true,
  "version_bumped": true,
  "second_confirmation": true,
  "admin_signature": "<signed approval token>",
  "timestamp": "2026-03-15T17:40:00Z"
}
```

### Example Approved Response

```json
{
  "accepted": true,
  "workflow": "create-production-builds.yml",
  "reason": "Release gate checks passed",
  "command": "npx eas-cli workflow:run create-production-builds.yml"
}
```

## Environment Variables

- `RELEASE_ALLOWED_USERS`: comma-separated requester allowlist
- `RELEASE_ADMIN_SIGNATURE`: expected administrative release token/signature for validation

## Governance Recommendation

Use two-step production authorization:

1. Voice command to prepare release
2. Explicit second confirmation
3. Administrative signature verification

This minimizes accidental or malicious production deployments.
