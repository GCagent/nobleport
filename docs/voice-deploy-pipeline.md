# Stephanie Voice-to-Release Pipeline for Berns (Expo/EAS)

This guide describes a production-ready flow for saying **"Stephanie deploy the Berns app"** and safely running an Expo/EAS production release.

## End-to-End Architecture

```text
Voice Command
   ↓
Stephanie Intent Parser
   ↓
Deploy Webhook API
   ↓
Release Gate (policy + checks)
   ↓
GitHub Action (EAS workflow)
   ↓
EAS Build + Submit + OTA Update
```

## 1) Voice command to structured intent

Example supported phrases:

- "Stephanie deploy the Berns app"
- "Stephanie release Berns production"
- "Stephanie ship Berns build"

Expected normalized intent payload:

```json
{
  "intent": "deploy_app",
  "app": "berns",
  "environment": "production",
  "requestedBy": "Michael",
  "source": "voice"
}
```

## 2) Stephanie webhook to Release Gate

Stephanie should not call EAS directly. Instead, send a signed request to a backend endpoint.

Example endpoint:

- `POST /deploy-app`

Example payload:

```json
{
  "app": "berns",
  "env": "production",
  "trigger": "voice",
  "requestedBy": "Michael",
  "requestId": "uuid-v4"
}
```

## 3) Release Gate safety checks (required)

Before triggering build automation, validate all of the following:

1. **Authentication**: requester is verified.
2. **Authorization**: requester has production deploy rights.
3. **Target validation**: `app=berns`, `env=production`.
4. **Repository state**: clean branch, no protected-branch drift.
5. **Quality gate**: CI status green for required checks.
6. **Versioning**: app version/build numbers already bumped.
7. **Two-step confirmation**: spoken or UI confirmation for production.

## 4) Trigger GitHub Action, not local shell build

For traceability and auditability, the Release Gate should trigger a GitHub Actions workflow via `workflow_dispatch` instead of running local `exec("eas ...")`.

Recommended trigger API:

- `POST /repos/{owner}/{repo}/actions/workflows/berns-production-release.yml/dispatches`

Minimal request body:

```json
{
  "ref": "main",
  "inputs": {
    "requestedBy": "Michael",
    "trigger": "voice",
    "requestId": "uuid-v4"
  }
}
```

## 5) GitHub Actions workflow for Expo/EAS

Create `.github/workflows/berns-production-release.yml`:

```yaml
name: Berns Production Release

on:
  workflow_dispatch:
    inputs:
      requestedBy:
        description: "Requester"
        required: true
      trigger:
        description: "Trigger source"
        required: true
      requestId:
        description: "Release request correlation ID"
        required: true

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: npm ci

      - name: Install EAS CLI
        run: npm i -g eas-cli

      - name: Validate release metadata
        run: |
          echo "requestId=${{ github.event.inputs.requestId }}"
          echo "requestedBy=${{ github.event.inputs.requestedBy }}"
          echo "trigger=${{ github.event.inputs.trigger }}"

      - name: Build Android
        run: eas build --platform android --profile production --non-interactive

      - name: Build iOS
        run: eas build --platform ios --profile production --non-interactive

      - name: Submit Android
        run: eas submit --platform android --non-interactive

      - name: Submit iOS
        run: eas submit --platform ios --non-interactive

      - name: OTA update
        run: eas update --branch production --message "Voice deploy: ${{ github.event.inputs.requestId }}"
```

## 6) Secret management

Set these repository secrets:

- `EXPO_TOKEN` (robot token with least privileges)
- `APPLE_APP_SPECIFIC_PASSWORD` (if required by your iOS submission path)
- Any Android service credentials needed by your submit profile

Do **not** send credentials from voice payloads.

## 7) Recommended production confirmation flow

1. User says: "Stephanie deploy Berns"
2. Stephanie responds: "Production deploy detected. Confirm release?"
3. User says: "Confirm"
4. Release Gate executes checks and dispatches workflow
5. Stephanie reports status updates from GitHub/EAS webhooks

## 8) Operational hardening (what teams often miss)

- **Rollback hooks**: if crash rate spikes after rollout, trigger previous OTA channel.
- **Release notes automation**: generate notes from merged PRs and commit metadata.
- **Post-deploy health checks**: monitor Sentry/Datadog and fail release ticket if thresholds exceed policy.
- **Audit trail**: persist `requestId`, requester, commit SHA, workflow run ID, and store submission IDs.
- **Policy as code**: keep deploy gate checks versioned and reviewed in source control.

## 9) Minimal implementation checklist

- [ ] Add release gate API endpoint with authz + confirmation support
- [ ] Add GitHub Actions workflow dispatch integration
- [ ] Configure Expo/App Store secrets in GitHub
- [ ] Add release status callbacks to Stephanie
- [ ] Add rollback automation and post-deploy monitoring gates

This architecture keeps the convenience of voice control while preserving production-grade safety and auditability.
