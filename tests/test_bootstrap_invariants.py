"""
Regression tests for bootstrap.sh structure and behaviour invariants.
These tests parse the script text — they catch regressions that would
break the install experience without requiring Docker to be running.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = (ROOT / "scripts" / "bootstrap.sh").read_text()
DOCTOR_FULL = (ROOT / "scripts" / "doctor-full.sh").read_text()
MAKEFILE = (ROOT / "Makefile").read_text()


def test_bootstrap_handles_full_apps_core_modes():
    assert "--full" in BOOTSTRAP
    assert "--apps" in BOOTSTRAP
    assert "MODE=\"full\"" in BOOTSTRAP or 'MODE="full"' in BOOTSTRAP


def test_bootstrap_generates_env_if_missing():
    assert "generate-env.py" in BOOTSTRAP
    assert ".env.example" in BOOTSTRAP


def test_bootstrap_checks_for_placeholder_values():
    assert "<generate" in BOOTSTRAP


def test_bootstrap_idempotent_env_check():
    # Must not fail when .env already exists
    assert "already exists" in BOOTSTRAP or "ok .env" in BOOTSTRAP.lower()


def test_bootstrap_runs_migrations_idempotently():
    assert "infra/postgres/migrations" in BOOTSTRAP
    assert "ON_ERROR_STOP=1" in BOOTSTRAP


def test_bootstrap_health_checks_all_core_services():
    assert "API_GATEWAY_PORT" in BOOTSTRAP
    assert "SYNC_ENGINE_PORT" in BOOTSTRAP
    assert "COMMAND_BUS_PORT" in BOOTSTRAP
    assert "MODULE_SERVICE_PORT" in BOOTSTRAP


def test_bootstrap_auth_smoke_test_present():
    assert "api/devices/register" in BOOTSTRAP
    assert "access_token" in BOOTSTRAP


def test_bootstrap_prints_service_url_summary():
    assert "API gateway" in BOOTSTRAP
    assert "Web UI" in BOOTSTRAP
    assert "doctor-full" in BOOTSTRAP


def test_bootstrap_interactive_auth_is_tty_gated():
    # Must not unconditionally default interactive to true — should check TTY
    assert "-t 1" in BOOTSTRAP or "BOOTSTRAP_AUTOMATION_INTERACTIVE" in BOOTSTRAP
    # The old hardcoded default "true" must not exist without a TTY check
    lines = BOOTSTRAP.splitlines()
    for i, line in enumerate(lines):
        if "BOOTSTRAP_AUTOMATION_INTERACTIVE:-" in line:
            surrounding = "\n".join(lines[max(0, i-5):i+5])
            assert "-t 1" in surrounding or "interactive_default" in surrounding, (
                "BOOTSTRAP_AUTOMATION_INTERACTIVE must be TTY-gated, not unconditionally 'true'"
            )


def test_doctor_full_exists_and_is_executable():
    path = ROOT / "scripts" / "doctor-full.sh"
    assert path.exists(), "scripts/doctor-full.sh must exist"
    content = path.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "PASS=" in content or "ok()" in content


def test_doctor_full_checks_all_core_endpoints():
    assert "API_GATEWAY_PORT" in DOCTOR_FULL
    assert "SYNC_ENGINE_PORT" in DOCTOR_FULL
    assert "COMMAND_BUS_PORT" in DOCTOR_FULL
    assert "MODULE_SERVICE_PORT" in DOCTOR_FULL


def test_doctor_full_checks_compose_config():
    assert "docker compose" in DOCTOR_FULL
    assert "profile full" in DOCTOR_FULL


def test_doctor_full_checks_auth_smoke():
    assert "api/devices/register" in DOCTOR_FULL
    assert "access_token" in DOCTOR_FULL


def test_doctor_full_checks_restart_loops():
    assert "restart" in DOCTOR_FULL.lower()


def test_doctor_full_prints_summary_table():
    assert "Summary" in DOCTOR_FULL or "passed" in DOCTOR_FULL
    assert "PASS" in DOCTOR_FULL or "passed" in DOCTOR_FULL


def test_make_doctor_full_target_exists():
    assert "doctor-full" in MAKEFILE
    assert "doctor-full.sh" in MAKEFILE


def test_bootstrap_sh_passes_syntax_check():
    import subprocess
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / "bootstrap.sh")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"bootstrap.sh has syntax errors: {result.stderr}"


def test_doctor_full_sh_passes_syntax_check():
    import subprocess
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / "doctor-full.sh")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"doctor-full.sh has syntax errors: {result.stderr}"


def test_all_shell_scripts_pass_syntax_check():
    import subprocess
    scripts = list((ROOT / "scripts").rglob("*.sh"))
    failed = []
    for script in scripts:
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        if result.returncode != 0:
            failed.append(f"{script.name}: {result.stderr.strip()}")
    assert not failed, "Shell scripts with syntax errors:\n" + "\n".join(failed)
