import base64
import json

import pytest
from fastapi import HTTPException

from app import security


def test_jwt_round_trip_and_scope_check():
    token = security.issue_token("profile", "device", ["sync:read"], ttl_seconds=60)
    payload = security.verify_token(token)
    assert payload["sub"] == "profile"
    assert payload["device_id"] == "device"
    assert payload["scopes"] == ["sync:read"]
    principal = security.Principal(subject="profile", device_id="device", scopes=payload["scopes"])
    security.require_scope(principal, "sync:read")
    with pytest.raises(HTTPException):
        security.require_scope(principal, "sync:write")


def test_wildcard_scope_allows_everything():
    security.require_scope(security.Principal("local", None, ["*"]), "admin:anything")


def test_jwt_rejects_tampering_and_expiry_and_type_mismatch():
    token = security.issue_token("profile", "device", ["sync:read"], ttl_seconds=60)
    bad = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(HTTPException):
        security.verify_token(bad)
    expired = security.issue_token("profile", "device", ["sync:read"], ttl_seconds=-10)
    with pytest.raises(HTTPException):
        security.verify_token(expired)
    refresh = security.issue_token("profile", "device", ["sync:read"], ttl_seconds=60, token_type="refresh")
    with pytest.raises(HTTPException):
        security.verify_token(refresh, expected_type="access")


def test_optional_principal_and_bearer_extraction():
    assert security.optional_principal(None).subject == "local-dev"
    token = security.issue_token("profile", "device", ["modules:read"], ttl_seconds=60)
    principal = security.optional_principal(f"Bearer {token}")
    assert principal.subject == "profile"
    assert security.extract_bearer_token("Bearer abc") == "abc"
    assert security.token_hash("abc") == security.token_hash("abc")
    with pytest.raises(HTTPException):
        security.extract_bearer_token("Basic abc")
    with pytest.raises(HTTPException):
        security.optional_principal("Basic abc")


def test_decode_token_parts_and_malformed_token():
    token = security.issue_token("profile", None, ["device"], ttl_seconds=60)
    header, payload, sig = security.decode_token_parts(token)
    assert header["alg"] == "HS256"
    assert payload["device_id"] is None
    assert sig
    with pytest.raises(HTTPException):
        security.decode_token_parts("not-a-jwt")


def test_invalid_audience_is_rejected():
    token = security.issue_token("profile", "device", ["sync:read"], ttl_seconds=60)
    head, body, sig = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    payload["aud"] = "wrong"
    new_body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    with pytest.raises(HTTPException):
        security.verify_token(f"{head}.{new_body}.{sig}")


def test_key_ring_loader_and_unknown_key(monkeypatch):
    monkeypatch.setenv('JWT_KEY_RING', '{"a":"secret"}')
    assert security._load_key_ring() == {'a': 'secret'}
    monkeypatch.setenv('JWT_KEY_RING', 'not-json')
    with pytest.raises(RuntimeError):
        security._load_key_ring()
    with pytest.raises(RuntimeError):
        security.issue_token('profile', 'device', ['x'], key_id='missing')


def test_verify_rejects_unknown_kid_and_future_nbf():
    token = security.issue_token('profile', 'device', ['sync:read'], ttl_seconds=60)
    head, body, sig = token.split('.')
    header = json.loads(base64.urlsafe_b64decode(head + '=' * (-len(head) % 4)))
    header['kid'] = 'missing'
    bad_head = security._b64e(json.dumps(header).encode())
    with pytest.raises(HTTPException):
        security.verify_token(f'{bad_head}.{body}.{sig}')

    header = {"alg": "HS256", "typ": "JWT", "kid": security.ACTIVE_JWT_KID}
    payload = security.verify_token(token)
    payload['nbf'] = payload['exp'] + 1000
    signing_input = f"{security._b64e(security._json_dumps(header).encode())}.{security._b64e(security._json_dumps(payload).encode())}"
    import hmac, hashlib
    signed = hmac.new(security.JWT_KEYS[security.ACTIVE_JWT_KID].encode(), signing_input.encode(), hashlib.sha256).digest()
    with pytest.raises(HTTPException):
        security.verify_token(f"{signing_input}.{security._b64e(signed)}")


def test_require_principal_and_missing_auth(monkeypatch):
    with pytest.raises(HTTPException):
        security.require_principal(None)
    assert security.extract_bearer_token(None) is None
    monkeypatch.setattr(security, 'AUTH_REQUIRED', True)
    with pytest.raises(HTTPException):
        security.optional_principal(None)
