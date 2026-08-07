# Steph Bot — Telegram Operator

Status: **STAGED / CODED / NOT LIVE VERIFIED**

Steph Bot is a Telegram-facing conversational operator for NoblePort. It supports text, voice transcription + TTS replies, screenshot analysis, persistent per-chat memory, and read-only repository auditing.

## Safety and governance

- Unknown Telegram users are denied by default.
- `TELEGRAM_ALLOWED_USER_IDS` is mandatory.
- API keys and bot tokens are environment secrets only.
- The bot never runs arbitrary shell commands.
- Repository audit is read-only and implemented with Python file inspection.
- Production deployment, financial writes, custody, token transfers, securities actions, permit approvals, and contract signing remain human-gated and fail-closed.
- Telegram cannot promote an integration to LIVE VERIFIED.

## Required environment variables

- `TELEGRAM_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS` — comma-separated numeric Telegram user IDs
- `OPENAI_API_KEY`

Optional:

- `REPO_PATH` — defaults to current working directory
- `STEPH_MEMORY_DB` — defaults to `./steph_bot_memory.sqlite3`
- `OPENAI_TEXT_MODEL` — defaults to `gpt-5-mini`
- `OPENAI_VISION_MODEL` — defaults to the text model
- `OPENAI_TRANSCRIBE_MODEL` — defaults to `gpt-4o-mini-transcribe`
- `OPENAI_TTS_MODEL` — defaults to `gpt-4o-mini-tts`
- `OPENAI_TTS_VOICE` — defaults to `alloy`

## Operator commands

- `/start` — capability summary
- `/audit` — read-only repository audit
- `/deploy` — human-approved deployment gate/checklist
- Plain text — engineering conversation
- Voice note — transcription, AI response, optional TTS reply
- Photo/screenshot — vision analysis

## Evidence gates for LIVE VERIFIED

A deployment remains STAGED until all of the following are captured:

1. Telegram bot identity and intended operator allowlist recorded.
2. Secret configuration confirmed without exposing values.
3. Bot process starts successfully.
4. `/start` response captured with timestamp.
5. Authorized-user test passes and unauthorized-user test is rejected.
6. Text conversation succeeds.
7. Voice transcription succeeds.
8. TTS voice response succeeds.
9. Screenshot/vision test succeeds.
10. `/audit` proves read-only behavior.
11. Restart confirms memory persistence.
12. Deployment health evidence and rollback procedure are recorded.

Only then should the Telegram channel be promoted from STAGED to LIVE VERIFIED in the NoblePort Integration Status register.
