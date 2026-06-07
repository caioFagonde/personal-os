from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_connector_oauth_start_handles_missing_client_as_actionable_409():
    main = ROOT / "services/connector-service/app/main.py"
    text = main.read_text()
    assert "missing_oauth_client_detail" in text
    assert "HTTPException(status_code=409" in text
    assert "required_env" in text
    assert "GOOGLE_CLIENT_ID" in text
    assert "MICROSOFT_CLIENT_ID" in text


def test_connectors_page_does_not_call_oauth_for_unconfigured_provider_blindly():
    page = ROOT / "apps/web/src/pages/ConnectorsPage.vue"
    text = page.read_text()
    assert ':disable="!item.configured"' in text
    assert "Configure .env first" in text
    assert "describeConnectorError" in text
    assert "required_env" in text
