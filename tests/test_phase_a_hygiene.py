"""Phase A (Truth & Hygiene) contract tests.

These lock in the Phase A invariants: no personal data in source, env-driven
CORS, pairing-code enforcement wiring, canonical Command Center home, and
git-archive-based packaging.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- A1: PII purge -----------------------------------------------------------

def test_capture_service_has_no_hardcoded_personal_defaults():
    text = (ROOT / "services/capture-service/app/main.py").read_text()
    assert 'os.environ.get("SECRETARY_EMAIL", "")' in text
    assert 'os.environ.get("SECRETARY_WHATSAPP", "")' in text
    # no real-looking email or phone literals anywhere in the service
    assert not re.search(r"[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|yahoo)\.", text)
    assert not re.search(r"\+\d{10,15}", text)


def test_capture_service_warns_at_startup_when_delegation_unconfigured():
    text = (ROOT / "services/capture-service/app/main.py").read_text()
    assert "SECRETARY_EMAIL / SECRETARY_WHATSAPP are not set" in text
    assert "missing_channels" in text  # fail-closed structured 409 remains


def test_check_secrets_scans_for_personal_data():
    text = (ROOT / "scripts/check-secrets.sh").read_text()
    assert "EMAIL_PATTERN" in text
    assert "PHONE_PATTERN" in text


def test_env_example_ships_empty_secretary_values():
    env = (ROOT / ".env.example").read_text()
    assert "SECRETARY_EMAIL=\n" in env
    assert "SECRETARY_WHATSAPP=\n" in env


# --- A3: canonical home ------------------------------------------------------

def test_ambient_mode_route_exists_for_big_picture():
    routes = (ROOT / "apps/web/src/router/routes.ts").read_text()
    assert "{ path: '/ambient', component: BigPictureHome }" in routes


def test_command_center_links_to_ambient_mode():
    text = (ROOT / "apps/web/src/pages/CommandCenterPage.vue").read_text()
    assert 'to="/ambient"' in text


# --- A4: CORS + pairing ------------------------------------------------------

def test_all_services_read_cors_origins_from_env():
    for main in sorted((ROOT / "services").glob("*/app/main.py")):
        text = main.read_text()
        if "CORSMiddleware" not in text:
            continue
        assert "CORS_ALLOW_ORIGINS" in text, f"{main} has hardcoded CORS origins"
        assert 'allow_origins=["*"]' not in text, f"{main} has hardcoded wildcard origins"


def test_gateway_enforces_pairing_codes_when_auth_required():
    text = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "REQUIRE_DEVICE_PAIRING" in text
    assert "pairing_required" in text
    assert "invalid_pairing_code" in text
    assert "device_pairing_codes" in text
    # code must be single-use: consumed after successful registration
    assert "consumed_at=now()" in text


def test_registration_payload_supports_pairing_code():
    gateway = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "pairing_code: str | None" in gateway
    auth_ts = (ROOT / "apps/web/src/services/auth.ts").read_text()
    assert "pairing_code" in auth_ts
    assert "sessionStorage" in auth_ts  # never localStorage for pairing codes


def test_intelligence_service_has_tests():
    tests_dir = ROOT / "services/intelligence-service/tests"
    assert tests_dir.is_dir()
    assert list(tests_dir.glob("test_*.py")), "intelligence-service must keep behavioral tests"


# --- A5: packaging -----------------------------------------------------------

def test_makefile_packages_via_git_archive():
    makefile = (ROOT / "Makefile").read_text()
    assert "git archive" in makefile
    assert "package" in makefile


def test_gitignore_covers_secret_and_runtime_paths():
    gitignore = (ROOT / ".gitignore").read_text()
    for entry in (".env", "secrets/", ".private/", "data/", "backups/", "logs/", "node_modules/"):
        assert entry in gitignore, f".gitignore missing {entry}"
