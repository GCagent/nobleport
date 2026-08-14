import ast
from pathlib import Path

BOT = Path(__file__).resolve().parents[1] / "bots" / "steph_bot.py"


def source() -> str:
    assert BOT.exists(), "Steph bot module is missing"
    return BOT.read_text(encoding="utf-8")


def test_no_shell_execution_imports():
    tree = ast.parse(source())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "subprocess" not in imported
    assert "os.system" not in source()


def test_secrets_are_environment_driven():
    text = source()
    assert "TELEGRAM_TOKEN" in text
    assert "OPENAI_API_KEY" in text
    assert "NOBLEPORT_API_TOKEN" in text
    assert "YOUR_BOT_TOKEN" not in text
    assert "sk-" not in text


def test_allowlist_fails_closed():
    text = source()
    assert "TELEGRAM_ALLOWED_USER_IDS" in text
    assert "fails closed" in text.lower()


def test_gated_action_language_present():
    text = source().lower()
    assert "explicit human approval" in text
    assert "release funds" in text
    assert "send tokens" in text
    assert "production deployment" in text


def test_status_and_geometry_commands_registered():
    text = source()
    assert 'CommandHandler("status"' in text
    assert 'CommandHandler("geometry"' in text
