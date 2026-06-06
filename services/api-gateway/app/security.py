from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException

JWT_ISSUER = os.environ.get("JWT_ISSUER", "personal-os-local")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "personal-os")
JWT_SECRET = os.environ.get("JWT_SECRET", "local-dev-only-change-me")
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() in {"1", "true", "yes"}


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def issue_token(subject: str, device_id: str, scopes: list[str], ttl_seconds: int = 86400) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": subject,
        "device_id": device_id,
        "scopes": scopes,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    signing_input = f"{_b64e(json.dumps(header, separators=(',', ':')).encode())}.{_b64e(json.dumps(payload, separators=(',', ':')).encode())}"
    sig = hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64e(sig)}"


def verify_token(token: str) -> dict[str, Any]:
    try:
        head, body, sig = token.split(".")
        signing_input = f"{head}.{body}"
        expected = _b64e(hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature mismatch")
        payload = json.loads(_b64d(body))
        if payload.get("iss") != JWT_ISSUER or payload.get("aud") != JWT_AUDIENCE:
            raise ValueError("issuer or audience mismatch")
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc


@dataclass(frozen=True)
class Principal:
    subject: str
    device_id: str | None
    scopes: list[str]


def optional_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization:
        if AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="missing bearer token")
        return Principal(subject="local-dev", device_id=None, scopes=["*"])
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization header")
    payload = verify_token(token)
    return Principal(subject=str(payload.get("sub")), device_id=payload.get("device_id"), scopes=list(payload.get("scopes", [])))


def require_scope(principal: Principal, scope: str) -> None:
    if "*" not in principal.scopes and scope not in principal.scopes:
        raise HTTPException(status_code=403, detail=f"missing scope: {scope}")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
