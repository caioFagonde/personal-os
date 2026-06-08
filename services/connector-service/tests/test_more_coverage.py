import pytest
from cryptography.fernet import Fernet

from app.backup import validate_restore_manifest
from app.oauth import (
    OAuthConfig,
    build_authorization_start,
    make_code_verifier,
    make_state,
    refresh_payload,
    token_endpoint,
    token_exchange_payload,
)
from app.providers import provider_status_from_env, twilio_auth_header, twilio_message_payload


def test_state_and_verifier_shape():
    assert make_state("x").startswith("x_")
    verifier = make_code_verifier()
    assert 43 <= len(verifier) <= 128


def test_oauth_config_validation():
    with pytest.raises(ValueError):
        build_authorization_start(OAuthConfig("google", "", "", "http://cb", ()))
    with pytest.raises(ValueError):
        build_authorization_start(OAuthConfig("google", "id", "", "", ()))
    with pytest.raises(ValueError):
        build_authorization_start(OAuthConfig("bad", "id", "", "http://cb", ()))


def test_token_endpoint_and_payload_errors():
    assert token_endpoint("google").endswith("token")
    assert "common" in token_endpoint("microsoft")
    with pytest.raises(ValueError):
        token_endpoint("bad")
    cfg = OAuthConfig("google", "id", "secret", "http://cb", ())
    with pytest.raises(ValueError):
        token_exchange_payload(cfg, code="", code_verifier="verifier")
    assert token_exchange_payload(cfg, code="abc", code_verifier="verifier")["client_secret"] == "secret"


def test_refresh_payloads():
    google = OAuthConfig("google", "gid", "secret", "http://cb", ())
    assert refresh_payload(google, refresh_token="rt")["grant_type"] == "refresh_token"
    ms = OAuthConfig("microsoft", "mid", "secret", "http://cb", ("User.Read",))
    payload = refresh_payload(ms, refresh_token="rt")
    assert "offline_access" in payload["scope"]


def test_provider_status_all_branches_and_errors():
    assert provider_status_from_env({"TWILIO_ACCOUNT_SID":"AC", "TWILIO_AUTH_TOKEN":"tok", "TWILIO_WHATSAPP_FROM":"whatsapp:+14155238886"}, "twilio").configured
    assert not provider_status_from_env({}, "twilio").configured
    assert provider_status_from_env({"GOOGLE_CLIENT_ID":"id", "GOOGLE_CLIENT_SECRET":"sec", "GOOGLE_REDIRECT_URI":"http://cb"}, "google").configured
    assert provider_status_from_env({"MICROSOFT_CLIENT_ID":"id", "MICROSOFT_CLIENT_SECRET":"sec", "MICROSOFT_REDIRECT_URI":"http://cb"}, "microsoft").configured
    with pytest.raises(ValueError):
        provider_status_from_env({}, "unknown")


def test_twilio_validation_errors():
    with pytest.raises(ValueError):
        twilio_auth_header("", "")
    with pytest.raises(ValueError):
        twilio_message_payload(to="+5511999999999", body="", from_="whatsapp:+14155238886")
    with pytest.raises(ValueError):
        twilio_message_payload(to="not-a-number", body="ok", from_="whatsapp:+14155238886")


def test_validate_restore_manifest_rejects_bad_shapes():
    assert not validate_restore_manifest({})
    assert not validate_restore_manifest({"backup_id":"b", "archive_path":"a", "sha256":"s", "created_at":1, "included_paths":"docs"})


def test_default_scope_branches_and_missing_include():
    from app.oauth import normalize_scopes, build_authorization_start
    assert "https://www.googleapis.com/auth/drive.file" in normalize_scopes("google", None)
    assert "User.Read" in normalize_scopes("microsoft", None)
    # Requested google scopes are prepended with OIDC essentials if missing.
    scopes = normalize_scopes("google", ["https://www.googleapis.com/auth/drive.file"])
    assert scopes[:3] == ("openid", "email", "profile")
    with pytest.raises(ValueError):
        build_authorization_start(OAuthConfig("unknown", "id", "", "http://cb", ()))


def test_backup_skips_missing_paths(tmp_path):
    from app.backup import create_backup_bundle
    root = tmp_path / "repo"; root.mkdir()
    manifest = create_backup_bundle(root, tmp_path / "backups", include=["missing"], encryption_key=Fernet.generate_key().decode())
    assert manifest.included_paths == ()
