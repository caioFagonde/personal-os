import pytest

from app.service_identity import issue_service_token, service_auth_header, verify_service_token


def test_service_token_round_trip_with_scope():
    token = issue_service_token("sync-engine", ["events:publish", "sync:write"], issued_at=1000, ttl_seconds=60)
    principal = verify_service_token(token, required_scope="events:publish", now=1010)
    assert principal.service == "sync-engine"
    assert principal.expires_at == 1060
    assert "sync:write" in principal.scopes


def test_service_token_rejects_missing_scope():
    token = issue_service_token("module-service", ["module:read"], issued_at=1000, ttl_seconds=60)
    with pytest.raises(PermissionError):
        verify_service_token(token, required_scope="module:write", now=1010)


def test_service_token_rejects_expired_and_tampered_tokens():
    token = issue_service_token("automation-service", ["*"], issued_at=1000, ttl_seconds=1)
    with pytest.raises(ValueError):
        verify_service_token(token, now=1005)
    with pytest.raises(ValueError):
        verify_service_token(token[:-2] + "xx", now=1000)


def test_service_auth_header_shape():
    header = service_auth_header("api-gateway", ["health:write"])
    assert list(header) == ["x-personal-os-service-token"]
    assert verify_service_token(header["x-personal-os-service-token"], required_scope="health:write")


def test_service_name_and_ttl_are_bounded():
    with pytest.raises(ValueError):
        issue_service_token("bad service", ["*"])
    with pytest.raises(ValueError):
        issue_service_token("api", ["*"], ttl_seconds=0)
    with pytest.raises(ValueError):
        issue_service_token("api", ["*"], ttl_seconds=3601)
