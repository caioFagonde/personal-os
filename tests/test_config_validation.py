from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-env.py"
spec = importlib.util.spec_from_file_location("validate_env", SCRIPT)
assert spec and spec.loader
validate_env = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_env
spec.loader.exec_module(validate_env)


def errors(values: dict[str, str]) -> dict[str, str]:
    return {item.key: item.message for item in validate_env.validate_values(values) if item.level == "error"}


def test_detects_malformed_urls_ports_phones_and_redirects():
    found = errors(
        {
            "SERVICE_URL": "localhost:8080",
            "SERVICE_PORT": "70000",
            "ALERT_PHONE": "5551234",
            "TWILIO_WHATSAPP_FROM": "+15551234567",
            "GOOGLE_REDIRECT_URI": "https://localhost/callback#token",
        }
    )
    assert set(found) == {"SERVICE_URL", "SERVICE_PORT", "ALERT_PHONE", "TWILIO_WHATSAPP_FROM", "GOOGLE_REDIRECT_URI"}


def test_detects_azure_and_aws_shapes():
    found = errors(
        {
            "AWS_REGION": "east",
            "AWS_QUEUE_ARN": "queue",
            "AZURE_STORAGE_CONNECTION_STRING": "AccountName=only",
            "AZURE_TENANT_ID": "tenant",
        }
    )
    assert set(found) == {"AWS_REGION", "AWS_QUEUE_ARN", "AZURE_STORAGE_CONNECTION_STRING", "AZURE_TENANT_ID"}


def test_incomplete_optional_provider_is_warning_not_error():
    findings = validate_env.validate_values({"GOOGLE_CLIENT_ID": "client-id"})
    assert not [item for item in findings if item.level == "error"]
    assert any(item.level == "warning" and item.key == "Google OAuth" for item in findings)


def test_cli_never_prints_secret_value(tmp_path: Path):
    secret = "do-not-print-this-secret"
    env_file = tmp_path / "config"
    env_file.write_text(f"GOOGLE_CLIENT_SECRET={secret}\nGOOGLE_REDIRECT_URI=not-a-url\n")
    result = subprocess.run([sys.executable, str(SCRIPT), str(env_file)], capture_output=True, text=True)
    assert result.returncode == 1
    assert secret not in result.stdout + result.stderr
    assert "GOOGLE_REDIRECT_URI" in result.stdout


def test_doctor_runs_safe_validator_before_compose():
    doctor = (ROOT / "scripts" / "doctor-full.sh").read_text()
    assert doctor.index("scripts/validate-env.py") < doctor.index("docker compose")


def test_settings_ui_masks_validates_and_explains_restart():
    form = (ROOT / "apps/web/src/components/NexusConfigForm.vue").read_text()
    page = (ROOT / "apps/web/src/pages/SettingsPage.vue").read_text()
    assert "'password'" in form
    assert "E.164" in form
    assert "1 to 65535" in form
    assert "restarted" in form
    assert "restart connector-service" in page


def test_gateway_config_contract_is_actionable_and_redacted():
    config = (ROOT / "services/api-gateway/app/config_validation.py").read_text()
    main = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert '"masked": "********"' in config
    assert '"setup_path": "/settings"' in config
    assert '"optional_service_unavailable"' in main
    assert '{"value": payload.value}' not in main
