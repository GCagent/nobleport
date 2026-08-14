import importlib.util
from pathlib import Path

import httpx
import pytest

BOT = Path(__file__).resolve().parents[1] / "bots" / "steph_bot.py"


def load_bot():
    assert BOT.exists(), "Steph bot module is missing"
    spec = importlib.util.spec_from_file_location("steph_bot_under_test", BOT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_settings_fail_closed_without_operator_allowlist(monkeypatch):
    bot = load_bot()
    monkeypatch.setenv("TELEGRAM_TOKEN", "telegram-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    with pytest.raises(RuntimeError, match="fails closed"):
        bot.BotSettings.from_env()


@pytest.mark.asyncio
async def test_nobleport_status_reports_unconfigured_connection():
    bot = load_bot()
    client = bot.NoblePortClient(base_url="", api_token="")
    result = await client.status()
    assert result == {
        "configured": False,
        "connected": False,
        "authenticated": False,
        "detail": "NoblePort API URL/token not configured",
    }


@pytest.mark.asyncio
async def test_nobleport_status_uses_authenticated_gcagent_probe():
    bot = load_bot()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/gcagent/schema"
        assert request.headers["Authorization"] == "Bearer gcagent-test-token"
        return httpx.Response(200, json={"postgres_schema_sql": "CREATE TABLE test"})

    transport = httpx.MockTransport(handler)
    client = bot.NoblePortClient(
        base_url="https://nobleport.test",
        api_token="gcagent-test-token",
        transport=transport,
    )
    result = await client.status()
    assert result["configured"] is True
    assert result["connected"] is True
    assert result["authenticated"] is True
    assert result["detail"] == "GCagent authenticated"


def test_geometry_health_check_uses_verified_reasoning_gate():
    bot = load_bot()
    result = bot.geometry_health_check()
    assert result["engine"] == "geometric_reasoning"
    assert result["status"] == "committed"
    assert result["review_required"] is False
    assert result["centerline_offset_m"] == 0.0
