from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_heredoc_does_not_expand_demo_token_under_set_u():
    text = (ROOT / "scripts/bootstrap.sh").read_text()
    assert 'TOKEN=$(curl -fsS -X POST http://localhost:${API_GATEWAY_PORT:-8080}/api/devices/register' not in text
    assert 'TOKEN=\\$(curl -fsS -X POST http://localhost:${API_GATEWAY_PORT:-8080}/api/devices/register' in text
    assert 'authorization: Bearer \\$TOKEN' in text


def test_api_gateway_decodes_asyncpg_jsonb_strings_for_modules():
    text = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "def json_value" in text
    assert 'manifest = json_value(row["manifest"], {})' in text
    assert 'routes = json_value(row["routes"], {})' in text
    assert 'dict(row["manifest"])' not in text
    assert 'dict(row["routes"])' not in text
