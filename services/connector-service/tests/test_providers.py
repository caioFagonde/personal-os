import base64

import pytest

from app.providers import (
    normalize_whatsapp_address,
    provider_status_from_env,
    twilio_auth_header,
    twilio_message_payload,
    validate_obsidian_vault_path,
)


def test_normalize_whatsapp_address_requires_e164():
    assert normalize_whatsapp_address("+5511999999999") == "whatsapp:+5511999999999"
    assert normalize_whatsapp_address("whatsapp:+5511999999999") == "whatsapp:+5511999999999"
    with pytest.raises(ValueError):
        normalize_whatsapp_address("11999999999")


def test_twilio_payload_uses_from_or_messaging_service():
    payload = twilio_message_payload(to="+5511999999999", body="hello", from_="whatsapp:+14155238886")
    assert payload["To"] == "whatsapp:+5511999999999"
    assert payload["From"] == "whatsapp:+14155238886"
    payload = twilio_message_payload(to="+5511999999999", body="hello", messaging_service_sid="MG123")
    assert payload["MessagingServiceSid"] == "MG123"
    with pytest.raises(ValueError):
        twilio_message_payload(to="+5511999999999", body="hello")


def test_twilio_auth_header_basic_auth():
    header = twilio_auth_header("AC123", "secret")
    expected = base64.b64encode(b"AC123:secret").decode()
    assert header == {"authorization": f"Basic {expected}"}


def test_provider_status_from_env():
    env = {"NTFY_BASE_URL": "http://ntfy", "NTFY_TOPIC": "topic"}
    assert provider_status_from_env(env, "ntfy").configured is True
    assert provider_status_from_env({}, "google").status == "needs_oauth_client"
    assert provider_status_from_env({"TAILSCALE_AUTHKEY": "tskey-auth-x"}, "tailscale").configured is True


def test_new_connector_status_metadata_does_not_expose_values():
    notion = provider_status_from_env({"NOTION_API_TOKEN": "private", "NOTION_DATABASE_ID": "db"}, "notion")
    assert notion.configured is True
    assert notion.required_env == ("NOTION_API_TOKEN",)
    assert notion.required_any_of == (("NOTION_DATABASE_ID", "NOTION_PAGE_ID"),)
    assert "private" not in repr(notion)

    trello = provider_status_from_env({}, "trello")
    assert trello.configured is False
    assert trello.capabilities == ("card_create_dry_run",)
    assert all(field["key"].startswith("TRELLO_") for field in trello.config_metadata)

    obsidian = provider_status_from_env({"OBSIDIAN_VAULT_PATH": "/vault"}, "obsidian")
    assert obsidian.configured is True
    assert "explicit_local_export" in obsidian.capabilities


def test_obsidian_path_validation_contains_markdown_paths(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _, target = validate_obsidian_vault_path(str(vault), "Zettelkasten/202606081200 Note.md")
    assert target == vault / "Zettelkasten" / "202606081200 Note.md"

    with pytest.raises(ValueError, match="inside"):
        validate_obsidian_vault_path(str(vault), "../outside.md")
    with pytest.raises(ValueError, match="Markdown"):
        validate_obsidian_vault_path(str(vault), "attachments/file.pdf")
    with pytest.raises(ValueError, match="absolute"):
        validate_obsidian_vault_path("relative/vault", "note.md")


def test_obsidian_path_validation_rejects_symlink_escape(tmp_path):
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    (vault / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="inside"):
        validate_obsidian_vault_path(str(vault), "linked/note.md")
