from urllib.parse import parse_qs, urlparse

import pytest

from app.oauth import OAuthConfig, build_authorization_start, code_challenge_s256, normalize_scopes, token_exchange_payload


def test_google_authorization_url_requests_offline_access_and_pkce():
    cfg = OAuthConfig("google", "gid", "secret", "http://localhost/callback", ())
    start = build_authorization_start(cfg, state="state1", code_verifier="verifier")
    parsed = urlparse(start.authorization_url)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert qs["access_type"] == ["offline"]
    assert qs["prompt"] == ["consent"]
    assert qs["state"] == ["state1"]
    assert qs["code_challenge"] == [code_challenge_s256("verifier")]
    assert "https://www.googleapis.com/auth/gmail.send" in qs["scope"][0]


def test_microsoft_scopes_always_include_offline_access():
    scopes = normalize_scopes("microsoft", ["User.Read"])
    assert "offline_access" in scopes
    cfg = OAuthConfig("microsoft", "mid", "secret", "http://localhost/callback", ("User.Read",), tenant="common")
    start = build_authorization_start(cfg, state="state2", code_verifier="verifier")
    qs = parse_qs(urlparse(start.authorization_url).query)
    assert qs["response_type"] == ["code"]
    assert "offline_access" in qs["scope"][0]
    assert qs["code_challenge_method"] == ["S256"]


def test_token_exchange_payload_excludes_empty_secret_for_public_client():
    cfg = OAuthConfig("google", "gid", "", "http://localhost/callback", ())
    payload = token_exchange_payload(cfg, code="abc", code_verifier="verifier")
    assert payload["grant_type"] == "authorization_code"
    assert payload["code_verifier"] == "verifier"
    assert "client_secret" not in payload


def test_unsupported_provider_rejected():
    with pytest.raises(ValueError):
        normalize_scopes("dropbox", None)
