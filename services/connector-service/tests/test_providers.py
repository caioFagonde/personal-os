import base64

import pytest

from app.providers import normalize_whatsapp_address, provider_status_from_env, twilio_auth_header, twilio_message_payload


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
