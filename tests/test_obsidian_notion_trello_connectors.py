from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "services/connector-service/app/main.py").read_text()
PROVIDERS = (ROOT / "services/connector-service/app/providers.py").read_text()
UI = (ROOT / "apps/web/src/pages/ConnectorsPage.vue").read_text()


def test_marketplace_lists_requested_connectors_and_metadata():
    assert '"obsidian", "notion", "trello"' in MAIN
    for provider in ("obsidian", "notion", "trello"):
        assert f'"{provider}"' in PROVIDERS
        assert f"item.id === '{provider}'" in UI
    assert "config_metadata" in UI


def test_missing_config_contract_is_structured():
    assert "connector_missing_configuration" in MAIN
    assert '"missing_config"' in MAIN
    assert '"required_any_of"' in MAIN
    assert "configure_server_environment" in MAIN


def test_dry_run_routes_exist_and_default_to_no_external_writes():
    expected_routes = (
        "/api/connectors/obsidian/export",
        "/api/connectors/obsidian/import",
        "/api/connectors/obsidian/path/validate",
        "/api/connectors/notion/pages/dry-run",
        "/api/connectors/notion/export/dry-run",
        "/api/connectors/trello/cards/dry-run",
    )
    for route in expected_routes:
        assert route in MAIN
    assert MAIN.count("execute: bool = False") >= 5
    assert "connector_dry_run_only" in MAIN


def test_obsidian_write_is_explicit_and_contained():
    assert "validate_obsidian_vault_path" in MAIN
    assert "contained_in_vault" in MAIN
    assert "if not payload.execute" in MAIN
    assert 'target.open("x"' in MAIN
    assert "Refusing to overwrite" in MAIN


def test_connector_ui_does_not_store_provider_secrets_in_browser():
    assert "never stored in browser localStorage" in UI
    assert "localStorage.setItem" not in UI
    assert "runDryRun" in UI
