"""Stephanie Telegram operator for NoblePort Systems.

Capabilities:
- Authorized text chat through the OpenAI Responses API.
- Voice transcription and TTS replies.
- Vision analysis for field photos/screenshots.
- Local conversation memory.
- Read-only repository audit.
- Read-only authenticated GCagent API connectivity probe.
- Deterministic geometric-reasoning health check.

Governance:
- Telegram access fails closed through an explicit operator allowlist.
- Secrets are environment-only.
- No subprocess or arbitrary shell execution.
- Production deployment, release funds, send tokens, custody, permit approval,
  contract signing, or other sensitive actions require explicit human approval.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterable, Optional

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from api.geometric_reasoning import (
    BoundingBox,
    Evidence,
    GeometricEntity,
    Point3D,
    centered_on,
    verification_gate,
)

LOG = logging.getLogger("steph_bot")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

SYSTEM_PROMPT = """You are Steph, NoblePort's conversational engineering operator.
Be concise, practical, evidence-driven, and construction-aware. You may explain,
inspect, recommend, summarize, and prepare changes. Never claim an integration is
LIVE VERIFIED without primary runtime evidence. Production deployment, release
funds, send tokens, custody, securities execution, permit approval, and contract
signing require explicit human approval and remain fail-closed. Prefer measurable
before/after evidence for optimization work. Treat uncertain geometry as provisional
or held rather than silently promoting it to project truth.
"""


class BotSettings:
    """Runtime configuration loaded only when the bot starts."""

    def __init__(
        self,
        *,
        telegram_token: str,
        openai_api_key: str,
        allowed_user_ids: set[int],
        openai_text_model: str,
        openai_vision_model: str,
        openai_transcribe_model: str,
        openai_tts_model: str,
        openai_tts_voice: str,
        repo_path: Path,
        memory_db: Path,
        max_history: int,
        nobleport_api_url: str,
        nobleport_api_token: str,
    ) -> None:
        self.telegram_token = telegram_token
        self.openai_api_key = openai_api_key
        self.allowed_user_ids = allowed_user_ids
        self.openai_text_model = openai_text_model
        self.openai_vision_model = openai_vision_model
        self.openai_transcribe_model = openai_transcribe_model
        self.openai_tts_model = openai_tts_model
        self.openai_tts_voice = openai_tts_voice
        self.repo_path = repo_path
        self.memory_db = memory_db
        self.max_history = max_history
        self.nobleport_api_url = nobleport_api_url
        self.nobleport_api_token = nobleport_api_token

    @classmethod
    def from_env(cls) -> "BotSettings":
        telegram_token = os.getenv("TELEGRAM_TOKEN", "").strip()
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not telegram_token:
            raise RuntimeError("TELEGRAM_TOKEN must be configured")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY must be configured")

        allowed = _parse_allowlist(os.getenv("TELEGRAM_ALLOWED_USER_IDS", ""))
        if not allowed:
            raise RuntimeError(
                "TELEGRAM_ALLOWED_USER_IDS must be configured; Stephanie Bot fails closed by default"
            )

        text_model = os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini")
        return cls(
            telegram_token=telegram_token,
            openai_api_key=openai_api_key,
            allowed_user_ids=allowed,
            openai_text_model=text_model,
            openai_vision_model=os.getenv("OPENAI_VISION_MODEL", text_model),
            openai_transcribe_model=os.getenv(
                "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"
            ),
            openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
            repo_path=Path(os.getenv("REPO_PATH", ".")).resolve(),
            memory_db=Path(
                os.getenv("STEPH_MEMORY_DB", "./steph_bot_memory.sqlite3")
            ).resolve(),
            max_history=max(1, int(os.getenv("STEPH_MAX_HISTORY", "8"))),
            nobleport_api_url=os.getenv("NOBLEPORT_API_URL", "").strip(),
            nobleport_api_token=os.getenv("NOBLEPORT_API_TOKEN", "").strip(),
        )


def _parse_allowlist(raw: str) -> set[int]:
    users: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if item:
            users.add(int(item))
    return users


class NoblePortClient:
    """Read-only bot adapter for authenticated GCagent connectivity evidence."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.transport = transport

    async def status(self) -> dict[str, object]:
        if not self.base_url or not self.api_token:
            return {
                "configured": False,
                "connected": False,
                "authenticated": False,
                "detail": "NoblePort API URL/token not configured",
            }

        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(10.0, connect=5.0),
                transport=self.transport,
            ) as client:
                response = await client.get("/api/gcagent/schema")
        except httpx.HTTPError as exc:
            return {
                "configured": True,
                "connected": False,
                "authenticated": False,
                "detail": f"GCagent connection failed: {exc.__class__.__name__}",
            }

        if response.status_code == 200:
            return {
                "configured": True,
                "connected": True,
                "authenticated": True,
                "detail": "GCagent authenticated",
            }
        if response.status_code in {401, 403}:
            return {
                "configured": True,
                "connected": True,
                "authenticated": False,
                "detail": "GCagent reachable but authentication failed",
            }
        return {
            "configured": True,
            "connected": True,
            "authenticated": False,
            "detail": f"GCagent probe returned HTTP {response.status_code}",
        }


def geometry_health_check() -> dict[str, object]:
    """Exercise the current NoblePort geometric gate without mutating project state."""

    evidence = Evidence(
        extraction_confidence=0.99,
        cross_source_agreement=0.99,
        human_verified=True,
    )
    host = GeometricEntity(
        project_id="steph-health",
        revision="health",
        class_name="wall",
        centroid=Point3D(x=10.0, y=4.0, z=1.0),
        bbox=BoundingBox(
            min=Point3D(x=9.5, y=3.8, z=0.0),
            max=Point3D(x=10.5, y=4.2, z=2.0),
        ),
        evidence=evidence.model_copy(deep=True),
    )
    opening = GeometricEntity(
        project_id="steph-health",
        revision="health",
        class_name="window",
        centroid=Point3D(x=10.0, y=4.0, z=1.0),
        bbox=BoundingBox(
            min=Point3D(x=9.7, y=3.9, z=0.5),
            max=Point3D(x=10.3, y=4.1, z=1.5),
        ),
        evidence=evidence.model_copy(deep=True),
    )
    decision = verification_gate(
        extraction_confidence=opening.evidence.extraction_confidence,
        cross_source_agreement=opening.evidence.cross_source_agreement,
        human_verified=opening.evidence.human_verified,
    )
    relation = centered_on(opening, host, axis="x")
    return {
        "engine": "geometric_reasoning",
        "status": decision.status.value,
        "confidence": decision.composite_confidence,
        "review_required": decision.review_required,
        "centerline_offset_m": relation.geometric_predicate.value,
    }


def _settings(context: ContextTypes.DEFAULT_TYPE) -> BotSettings:
    settings = context.application.bot_data.get("settings")
    if not isinstance(settings, BotSettings):
        raise RuntimeError("Stephanie Bot settings are not initialized")
    return settings


def _nobleport_client(settings: BotSettings) -> NoblePortClient:
    return NoblePortClient(
        base_url=settings.nobleport_api_url,
        api_token=settings.nobleport_api_token,
    )


def _init_db(settings: BotSettings) -> None:
    settings.memory_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.memory_db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def _remember(settings: BotSettings, chat_id: int, role: str, content: str) -> None:
    with sqlite3.connect(settings.memory_db) as conn:
        conn.execute(
            "INSERT INTO messages(chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content[:12000]),
        )
        conn.commit()


def _history(settings: BotSettings, chat_id: int) -> list[dict[str, str]]:
    with sqlite3.connect(settings.memory_db) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, settings.max_history),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def _authorized(update: Update, settings: BotSettings) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.allowed_user_ids)


async def _require_auth(update: Update, settings: BotSettings) -> bool:
    if _authorized(update, settings):
        return True
    if update.effective_message:
        await update.effective_message.reply_text(
            "Stephanie Bot is locked to authorized NoblePort operators."
        )
    return False


async def _post_openai_json(settings: BotSettings, path: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0), headers=headers
    ) as client:
        response = await client.post(f"https://api.openai.com/v1/{path}", json=payload)
        response.raise_for_status()
        return response.json()


def _response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip() or "No response text returned."


async def chat_with_ai(settings: BotSettings, chat_id: int, prompt: str) -> str:
    await asyncio.to_thread(_remember, settings, chat_id, "user", prompt)
    history = await asyncio.to_thread(_history, settings, chat_id)
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    payload = {
        "model": settings.openai_text_model,
        "instructions": SYSTEM_PROMPT,
        "input": (
            f"Repository root: {settings.repo_path.name}. Repo inspection is read-only.\n"
            f"Recent conversation:\n{transcript}\nuser: {prompt}"
        ),
    }
    data = await _post_openai_json(settings, "responses", payload)
    text = _response_text(data)
    await asyncio.to_thread(_remember, settings, chat_id, "assistant", text)
    return text


def _code_files(root: Path) -> Iterable[Path]:
    ignored = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
    }
    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".sql",
            ".sol",
            ".md",
        }:
            yield path


def repo_audit(root: Path) -> str:
    if not root.exists():
        return f"Repo path does not exist: {root}"
    stats: list[tuple[int, str]] = []
    todo_count = 0
    file_count = 0
    for path in _code_files(root):
        file_count += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.count("\n") + 1
        todo_count += text.lower().count("todo") + text.lower().count("fixme")
        stats.append((lines, str(path.relative_to(root))))
    stats.sort(reverse=True)
    heavy = "\n".join(f"{lines:>6}  {name}" for lines, name in stats[:10])
    return (
        "Read-only repo audit\n"
        f"Files scanned: {file_count}\n"
        f"TODO/FIXME markers: {todo_count}\n\n"
        f"Largest files by lines:\n{heavy or 'No code files found.'}\n\n"
        "No commands were executed and no files were changed."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    await update.effective_message.reply_text(
        "Stephanie Bot online.\n\n"
        "/status — OpenAI, GCagent and geometry readiness\n"
        "/geometry — deterministic geometry health check\n"
        "/audit — read-only repository scan\n"
        "/deploy — human-gated deployment checklist\n"
        "Text — engineering/construction conversation\n"
        "Voice — transcription + spoken reply\n"
        "Photo — vision analysis"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    api = await _nobleport_client(settings).status()
    geometry = geometry_health_check()
    await update.effective_message.reply_text(
        "Stephanie status\n"
        f"OpenAI configured: yes\n"
        f"GCagent: {api['detail']}\n"
        f"Geometry: {geometry['status']} ({geometry['confidence']:.2f})\n"
        f"Memory: {settings.memory_db.name}\n"
        "Sensitive actions: human-gated"
    )


async def geometry_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    result = geometry_health_check()
    await update.effective_message.reply_text(
        "Geometry engine health\n"
        f"Status: {result['status']}\n"
        f"Confidence: {result['confidence']:.2f}\n"
        f"Centerline offset: {result['centerline_offset_m']} m\n"
        f"Human review required: {result['review_required']}"
    )


async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    result = await asyncio.to_thread(repo_audit, settings.repo_path)
    await update.effective_message.reply_text(result[:4000])


async def deploy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    await update.effective_message.reply_text(
        "Production deployment is human-gated. Stephanie can prepare and verify the rollout but will not execute production deployment from Telegram.\n\n"
        "Gate: tests pass → secrets present → branch/commit identified → rollback plan → explicit human approval → deploy → health check → evidence record."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    text = (update.effective_message.text or "").strip()
    lower = text.lower()
    sensitive_terms = (
        "deploy to prod",
        "deploy production",
        "release funds",
        "send tokens",
        "sign contract",
        "approve permit",
    )
    if any(term in lower for term in sensitive_terms):
        response = (
            "That action is gated. I can prepare the plan and evidence packet, but execution requires explicit human approval outside this Telegram command."
        )
    elif any(term in lower for term in ("audit repo", "optimize repo", "find bottleneck")):
        audit_text = await asyncio.to_thread(repo_audit, settings.repo_path)
        response = await chat_with_ai(
            settings,
            update.effective_chat.id,
            f"Review this read-only repo audit and prioritize optimizations:\n{audit_text}",
        )
    else:
        response = await chat_with_ai(settings, update.effective_chat.id, text)
    await update.effective_message.reply_text(response[:4000])


async def _transcribe(settings: BotSettings, path: Path) -> str:
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=10.0), headers=headers
    ) as client:
        with path.open("rb") as handle:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                data={"model": settings.openai_transcribe_model},
                files={"file": (path.name, handle, "audio/ogg")},
            )
        response.raise_for_status()
        return str(response.json().get("text", "")).strip()


async def _tts(settings: BotSettings, text: str, path: Path) -> None:
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_tts_model,
        "voice": settings.openai_tts_voice,
        "input": text[:3500],
        "response_format": "mp3",
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=10.0), headers=headers
    ) as client:
        response = await client.post("https://api.openai.com/v1/audio/speech", json=payload)
        response.raise_for_status()
        path.write_bytes(response.content)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    voice = update.effective_message.voice
    if voice is None:
        return
    with tempfile.TemporaryDirectory(prefix="steph-voice-") as tmp:
        in_path = Path(tmp) / "voice.ogg"
        out_path = Path(tmp) / "reply.mp3"
        telegram_file = await voice.get_file()
        await telegram_file.download_to_drive(in_path)
        transcript = await _transcribe(settings, in_path)
        answer = await chat_with_ai(
            settings, update.effective_chat.id, f"Voice message: {transcript}"
        )
        await update.effective_message.reply_text(
            f"Voice: {transcript}\n\nStephanie: {answer}"[:4000]
        )
        try:
            await _tts(settings, answer, out_path)
            with out_path.open("rb") as audio:
                await update.effective_message.reply_voice(voice=audio)
        except Exception:
            LOG.exception("TTS reply failed")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    if not await _require_auth(update, settings):
        return
    photos = update.effective_message.photo
    if not photos:
        return
    with tempfile.TemporaryDirectory(prefix="steph-vision-") as tmp:
        path = Path(tmp) / "image.jpg"
        telegram_file = await photos[-1].get_file()
        await telegram_file.download_to_drive(path)
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        caption = (
            update.effective_message.caption
            or "Analyze this field image for errors, risks, geometry, and optimization opportunities."
        )
        payload = {
            "model": settings.openai_vision_model,
            "instructions": SYSTEM_PROMPT,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": caption},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{encoded}",
                        },
                    ],
                }
            ],
        }
        data = await _post_openai_json(settings, "responses", payload)
        answer = _response_text(data)
        await asyncio.to_thread(
            _remember, settings, update.effective_chat.id, "assistant", answer
        )
        await update.effective_message.reply_text(answer[:4000])


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOG.exception("Telegram handler error", exc_info=context.error)


def build_application(settings: BotSettings) -> Application:
    _init_db(settings)
    app = Application.builder().token(settings.telegram_token).build()
    app.bot_data["settings"] = settings
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("geometry", geometry_command))
    app.add_handler(CommandHandler("audit", audit))
    app.add_handler(CommandHandler("deploy", deploy_plan))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    settings = BotSettings.from_env()
    app = build_application(settings)
    LOG.info("Stephanie Bot starting in polling mode")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
