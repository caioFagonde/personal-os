from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.sh"


def test_bootstrap_auth_smoke_executes_command_substitution_not_literal():
    text = BOOTSTRAP.read_text()
    assert 'AUTH_TOKEN="\\$(' not in text
    assert 'AUTH_RESPONSE="$(curl -fsS -X POST' in text
    assert 'AUTH_PAYLOAD=' in text
    assert '-d "${AUTH_PAYLOAD}"' in text


def test_bootstrap_next_instructions_escape_demo_token_only():
    text = BOOTSTRAP.read_text()
    assert 'TOKEN=\\$(curl -fsS -X POST' in text
    assert 'Bearer \\$TOKEN' in text


def test_bootstrap_script_has_valid_bash_syntax():
    import subprocess
    subprocess.run(["bash", "-n", str(BOOTSTRAP)], check=True)
