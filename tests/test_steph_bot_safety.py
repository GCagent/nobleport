import ast
from pathlib import Path

BOT = Path(__file__).resolve().parents[1] / "bots" / "steph_bot.py"


def source() -> str:
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
    assert 'os.environ["TELEGRAM_TOKEN"]' in text
    assert 'os.environ["OPENAI_API_KEY"]' in text
    assert "YOUR_BOT_TOKEN" not in text
    assert "sk-" not in text


def test_allowlist_fails_closed():
    text = source()
    assert "TELEGRAM_ALLOWED_USER_IDS must be configured" in text
    assert "user.id in ALLOWED_USER_IDS" in text


def test_gated_action_language_present():
    text = source().lower()
    assert "explicit human approval" in text
    assert "release funds" in text
    assert "send tokens" in text
