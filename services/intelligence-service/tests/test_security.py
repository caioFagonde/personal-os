from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from fastapi import HTTPException

from app import security


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _make_token(payload: dict, secret: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{body}".encode()
    sig = _b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def _valid_payload() -> dict:
    return {
        "iss": security.JWT_ISSUER,
        "aud": security.JWT_AUDIENCE,
        "sub": "profile-1",
        "device_id": "device-1",
        "scopes": ["intelligence:read"],
    }


class TestOptionalPrincipal:
    def test_local_dev_principal_without_auth(self, monkeypatch):
        monkeypatch.setattr(security, "AUTH_REQUIRED", False)
        principal = security.optional_principal(None)
        assert principal.subject == "local-dev"
        assert principal.scopes == ["*"]

    def test_missing_token_rejected_when_auth_required(self, monkeypatch):
        monkeypatch.setattr(security, "AUTH_REQUIRED", True)
        with pytest.raises(HTTPException) as exc:
            security.optional_principal(None)
        assert exc.value.status_code == 401

    def test_malformed_token_rejected(self):
        with pytest.raises(HTTPException) as exc:
            security.optional_principal("Bearer not-a-jwt")
        assert exc.value.status_code == 401

    def test_bad_signature_rejected(self):
        token = _make_token(_valid_payload(), "wrong-secret")
        with pytest.raises(HTTPException) as exc:
            security.optional_principal(f"Bearer {token}")
        assert exc.value.status_code == 401

    def test_wrong_audience_rejected(self):
        payload = _valid_payload()
        payload["aud"] = "someone-else"
        token = _make_token(payload, security.JWT_SECRET)
        with pytest.raises(HTTPException) as exc:
            security.optional_principal(f"Bearer {token}")
        assert exc.value.status_code == 401

    def test_valid_token_accepted(self):
        token = _make_token(_valid_payload(), security.JWT_SECRET)
        principal = security.optional_principal(f"Bearer {token}")
        assert principal.subject == "profile-1"
        assert "intelligence:read" in principal.scopes
