from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

from fastapi import HTTPException

AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() == "true"
JWT_SECRET = os.environ.get("JWT_SECRET", "local-dev-only")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "personal-os-local")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "personal-os")


@dataclass(frozen=True)
class Principal:
    subject: str
    device_id: str | None
    scopes: list[str]


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def optional_principal(authorization: str | None) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        if AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="missing bearer token")
        return Principal(subject="local-dev", device_id=None, scopes=["*"])
    token = authorization.split(" ", 1)[1].strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="malformed bearer token")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    supplied = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="invalid bearer token signature")
    payload = json.loads(_b64url_decode(parts[1]))
    if payload.get("iss") != JWT_ISSUER or payload.get("aud") != JWT_AUDIENCE:
        raise HTTPException(status_code=401, detail="invalid token audience")
    return Principal(subject=str(payload.get("sub", "unknown")), device_id=payload.get("device_id"), scopes=list(payload.get("scopes", [])))


def require_scope(principal: Principal, scope: str) -> None:
    if "*" in principal.scopes or scope in principal.scopes:
        return
    raise HTTPException(status_code=403, detail=f"missing required scope: {scope}")
