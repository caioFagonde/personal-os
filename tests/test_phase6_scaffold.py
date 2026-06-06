from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_phase6_files_exist():
    required = [
        "services/automation-service/app/main.py",
        "services/automation-service/app/dag.py",
        "services/automation-service/app/policy.py",
        "services/automation-service/app/executor.py",
        "services/automation-service/app/n8n_bridge.py",
        "infra/postgres/migrations/005_phase_6_automation.sql",
        "modules/automation/manifest.yaml",
        "apps/web/src/pages/AutomationPage.vue",
        ".github/workflows/phase6-automation.yml",
        "docs/phase-6-automation-agentic-workflows.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert not missing


def test_automation_manifest_contract():
    manifest = yaml.safe_load((ROOT / "modules/automation/manifest.yaml").read_text())
    assert manifest["id"] == "automation"
    assert manifest["routes"]["web"] == "/automation"
    assert "automation:read" in manifest["permissions"]
    assert "automation.workflow.completed" in manifest["events"]["publishes"]


def test_compose_contains_automation_service_and_gateway_env():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert "automation-service" in services
    assert "automation" in services["automation-service"]["profiles"]
    gateway_env = services["api-gateway"]["environment"]
    assert gateway_env["AUTOMATION_SERVICE_URL"] == "http://automation-service:8085"


def test_makefile_has_phase6_targets():
    text = (ROOT / "Makefile").read_text()
    assert "up-automation" in text
    assert "test-phase6" in text
    assert "cov-fail-under=96" in text


def test_env_has_unique_phase6_secret_placeholder():
    text = (ROOT / ".env.example").read_text()
    assert "N8N_WEBHOOK_SECRET=<generate-with-openssl-rand-hex-32>" in text
    assert "VITE_AUTOMATION_URL=http://localhost:8080/api/proxy/automation" in text
