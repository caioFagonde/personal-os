from pathlib import Path


def test_phase10_connector_scaffold_exists():
    required = [
        "services/connector-service/app/main.py",
        "services/connector-service/app/oauth.py",
        "services/connector-service/app/providers.py",
        "infra/postgres/migrations/009_phase_10_connectors_continuity.sql",
        "apps/web/src/pages/ConnectorsPage.vue",
        "apps/web/src/pages/OnboardingPage.vue",
        "apps/web/src/pages/BackupRestorePage.vue",
        "apps/web/src/pages/DevicePairingPage.vue",
        "modules/connectors/manifest.yaml",
    ]
    for rel in required:
        assert Path(rel).exists(), rel


def test_phase10_compose_wires_connector_service():
    text = Path("docker-compose.yml").read_text()
    assert "connector-service:" in text
    assert "CONNECTOR_SERVICE_URL" in text
    assert "personal-os-connector-service" in text


def test_phase10_env_has_redirects_and_public_url():
    text = Path(".env.example").read_text()
    assert "CONNECTOR_PUBLIC_BASE_URL" in text
    assert "/api/proxy/connectors/api/connectors/google/callback" in text
    assert "/api/proxy/connectors/api/connectors/microsoft/callback" in text


def test_phase10_gateway_proxy_present():
    text = Path("services/api-gateway/app/main.py").read_text()
    assert "proxy_connectors" in text
    assert "connectors:read" in text
    assert "connectors:write" in text
