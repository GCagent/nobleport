"""Steph Bot: Telegram voice/vision conversational operator for NoblePort.

Security posture:
- Default-deny Telegram user allowlist.
- Secrets only from environment variables.
- No arbitrary shell execution.
- Repo actions are read-only advisory audits.
- Deploy/payment/token/permit/contract execution remains human-gated.
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
from typing import Iterable

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

LOG = logging.getLogger("steph_bot")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", OPENAI_TEXT_MODEL)
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
REPO_PATH = Path(os.getenv("REPO_PATH", ".")).resolve()
MEMORY_DB = Path(os.getenv("STEPH_MEMORY_DB", "./steph_bot_memory.sqlite3")).resolve()
MAX_HISTORY = int(os.getenv("STEPH_MAX_HISTORY", "8"))


def _parse_allowlist(raw: str) -> set[int]:
    out: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if item:
            out.add(int(item))
    return out


ALLOWED_USER_IDS = _parse_allowlist(os.getenv("TELEGRAM_ALLOWED_USER_IDS", ""))
OPENAI_HEADERS = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

SYSTEM_PROMPT = """You are Steph, NoblePort's conversational engineering copilot.
Tone: warm, concise, authoritative, practical.
You may explain, inspect, recommend, and prepare changes. You do not claim an
integration is LIVE VERIFIED without primary evidence. Financial, custody,
token-transfer, securities, permit-approval, contract-signing, and production
deployment actions require explicit human approval and remain fail-closed.
Prefer measurable before/after benchmarks for optimization work.
"""


def _init_db() -> None:
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(MEMORY_DB) as conn:
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


def _remember(chat_id: int, role: str, content: str) -> None:
    with sqlite3.connect(MEMORY_DB) as conn:
        conn.execute(
            "INSERT INTO messages(chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content[:12000]),
        )
        conn.commit()


def _history(chat_id: int) -> list[dict[str, str]]:
    with sqlite3.connect(MEMORY_DB) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, MAX_HISTORY),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def _authorized(update: Update) -> bool:
    user = update.effective_user
    return bool(user and ALLOWED_USER_IDS and user.id in ALLOWED_USER_IDS)


async def _require_auth(update: Update) -> bool:
    if _authorized(update):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("Steph Bot is locked to authorized NoblePort operators.")
    return False


async def _post_openai_json(path: str, payload: dict) -> dict:
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, headers={**OPENAI_HEADERS, "Content-Type": "application/json"}) as client:
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


async def chat_with_ai(chat_id: int, prompt: str) -> str:
    await asyncio.to_thread(_remember, chat_id, "user", prompt)
    history = await asyncio.to_thread(_history, chat_id)
    repo_context = f"Repository root: {REPO_PATH.name}. This bot has read-only advisory repo inspection."
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    payload = {
        "model": OPENAI_TEXT_MODEL,
        "instructions": SYSTEM_PROMPT,
        "input": f"{repo_context}\nRecent conversation:\n{transcript}\nuser: {prompt}",
    }
    data = await _post_openai_json("responses", payload)
    text = _response_text(data)
    await asyncio.to_thread(_remember, chat_id, "assistant", text)
    return text


def _code_files(root: Path) -> Iterable[Path]:
    ignored = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".sql", ".sol", ".md"}:
            yield path


def repo_audit() -> str:
    if not REPO_PATH.exists():
        return f"Repo path does not exist: {REPO_PATH}"
    stats: list[tuple[int, str]] = []
    todo_count = 0
    file_count = 0
    for path in _code_files(REPO_PATH):
        file_count += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.count("\n") + 1
        todo_count += text.lower().count("todo") + text.lower().count("fixme")
        stats.append((lines, str(path.relative_to(REPO_PATH))))
    stats.sort(reverse=True)
    heavy = "\n".join(f"{lines:>6}  {name}" for lines, name in stats[:10]) or "No code files found."
    return (
        f"Read-only repo audit\n"
        f"Files scanned: {file_count}\n"
        f"TODO/FIXME markers: {todo_count}\n\n"
        f"Largest files by lines:\n{heavy}\n\n"
        "No commands were executed and no files were changed."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    await update.effective_message.reply_text(
        "Steph Bot online.\n\n"
        "Chat: engineering and NoblePort context\n"
        "Voice: transcribe and reply with audio\n"
        "Vision: analyze screenshots and error images\n"
        "Audit: /audit performs a read-only repo scan\n"
        "Deploy: /deploy prepares a human-approved deployment checklist"
    )


async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    result = await asyncio.to_thread(repo_audit)
    await update.effective_message.reply_text(result[:4000])


async def deploy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    await update.effective_message.reply_text(
        "Deployment is human-gated. Steph can prepare and verify the rollout, but will not remotely execute prod deployment from Telegram.\n\n"
        "Gate: tests pass → secrets present → branch/commit identified → rollback plan → explicit human approval → deploy → health check → evidence record."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    text = (update.effective_message.text or "").strip()
    lower = text.lower()
    if any(term in lower for term in ("audit repo", "optimize repo", "find bottleneck")):
        audit_text = await asyncio.to_thread(repo_audit)
        response = await chat_with_ai(update.effective_chat.id, f"Review this read-only repo audit and prioritize optimizations:\n{audit_text}")
    elif any(term in lower for term in ("deploy to prod", "deploy production", "release funds", "send tokens")):
        response = "That action is gated. I can prepare the deployment/payment plan and evidence packet, but execution requires explicit human approval outside this Telegram command."
    else:
        response = await chat_with_ai(update.effective_chat.id, text)
    await update.effective_message.reply_text(response[:4000])


async def _transcribe(path: Path) -> str:
    timeout = httpx.Timeout(90.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, headers=OPENAI_HEADERS) as client:
        with path.open("rb") as handle:
            files = {"file": (path.name, handle, "audio/ogg")}
            data = {"model": OPENAI_TRANSCRIBE_MODEL}
            response = await client.post("https://api.openai.com/v1/audio/transcriptions", data=data, files=files)
        response.raise_for_status()
        result = response.json()
        return str(result.get("text", "")).strip()


async def _tts(text: str, path: Path) -> None:
    timeout = httpx.Timeout(90.0, connect=10.0)
    payload = {
        "model": OPENAI_TTS_MODEL,
        "voice": OPENAI_TTS_VOICE,
        "input": text[:3500],
        "response_format": "mp3",
    }
    async with httpx.AsyncClient(timeout=timeout, headers={**OPENAI_HEADERS, "Content-Type": "application/json"}) as client:
        response = await client.post("https://api.openai.com/v1/audio/speech", json=payload)
        response.raise_for_status()
        path.write_bytes(response.content)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    voice = update.effective_message.voice
    if voice is None:
        return
    with tempfile.TemporaryDirectory(prefix="steph-voice-") as tmp:
        in_path = Path(tmp) / "voice.ogg"
        out_path = Path(tmp) / "reply.mp3"
        telegram_file = await voice.get_file()
        await telegram_file.download_to_drive(in_path)
        transcript = await _transcribe(in_path)
        answer = await chat_with_ai(update.effective_chat.id, f"Voice message: {transcript}")
        await update.effective_message.reply_text(f"Voice: {transcript}\n\nSteph: {answer}"[:4000])
        try:
            await _tts(answer, out_path)
            with out_path.open("rb") as audio:
                await update.effective_message.reply_voice(voice=audio)
        except Exception:
            LOG.exception("TTS reply failed")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_auth(update):
        return
    photos = update.effective_message.photo
    if not photos:
        return
    with tempfile.TemporaryDirectory(prefix="steph-vision-") as tmp:
        path = Path(tmp) / "image.jpg"
        telegram_file = await photos[-1].get_file()
        await telegram_file.download_to_drive(path)
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        caption = update.effective_message.caption or "Analyze this screenshot for errors, risks, and optimization opportunities."
        payload = {
            "model": OPENAI_VISION_MODEL,
            "instructions": SYSTEM_PROMPT,
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": caption},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"},
                ],
            }],
        }
        data = await _post_openai_json("responses", payload)
        answer = _response_text(data)
        await asyncio.to_thread(_remember, update.effective_chat.id, "assistant", answer)
        await update.effective_message.reply_text(answer[:4000])


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOG.exception("Telegram handler error", exc_info=context.error)


def main() -> None:
    if not ALLOWED_USER_IDS:
        raise RuntimeError("TELEGRAM_ALLOWED_USER_IDS must be configured; Steph Bot fails closed by default")
    _init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("audit", audit))
    app.add_handler(CommandHandler("deploy", deploy_plan))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)
    LOG.info("Steph Bot starting in polling mode")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
