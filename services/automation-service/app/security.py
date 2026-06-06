from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Header, HTTPException

JWT_ISSUER = os.environ.get("JWT_ISSUER", "personal-os-local")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "personal-os")
JWT_SECRET = os.environ.get("JWT_SECRET", "local-dev-only-change-me")
JWT_KID = os.environ.get("JWT_KID", "local-v1")
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() in {"1", "true", "yes"}


def _load_key_ring() -> dict[str, str]:
    raw = os.environ.get("JWT_KEY_RING", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed:
                return {str(k): str(v) for k, v in parsed.items() if v}
        except json.JSONDecodeError as exc:
            raise RuntimeError("JWT_KEY_RING must be valid JSON object") from exc
    return {JWT_KID: JWT_SECRET}


JWT_KEYS = _load_key_ring()
ACTIVE_JWT_KID = os.environ.get("ACTIVE_JWT_KID", JWT_KID if JWT_KID in JWT_KEYS else next(iter(JWT_KEYS)))


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def issue_token(
    subject: str,
    device_id: str | None,
    scopes: list[str],
    ttl_seconds: int = 86400,
    *,
    token_type: str = "access",
    key_id: str | None = None,
    jwt_id: str | None = None,
) -> str:
    now = int(time.time())
    kid = key_id or ACTIVE_JWT_KID
    if kid not in JWT_KEYS:
        raise RuntimeError(f"unknown JWT signing key id: {kid}")
    header = {"alg": "HS256", "typ": "JWT", "kid": kid}
    payload: dict[str, Any] = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": subject,
        "device_id": device_id,
        "scopes": sorted(set(scopes)),
        "typ": token_type,
        "jti": jwt_id or str(uuid.uuid4()),
        "iat": now,
        "nbf": now - 5,
        "exp": now + ttl_seconds,
    }
    signing_input = f"{_b64e(_json_dumps(header).encode())}.{_b64e(_json_dumps(payload).encode())}"
    sig = hmac.new(JWT_KEYS[kid].encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64e(sig)}"


def decode_token_parts(token: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    try:
        head, body, sig = token.split(".")
        return json.loads(_b64d(head)), json.loads(_b64d(body)), sig
    except Exception as exc:
        raise HTTPException(status_code=401, detail="malformed bearer token") from exc


def verify_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    try:
        head, body, sig = token.split(".")
        header = json.loads(_b64d(head))
        payload = json.loads(_b64d(body))
        kid = str(header.get("kid", JWT_KID))
        secret = JWT_KEYS.get(kid)
        if not secret:
            raise ValueError("unknown signing key")
        signing_input = f"{head}.{body}"
        expected = _b64e(hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature mismatch")
        now = int(time.time())
        if payload.get("iss") != JWT_ISSUER or payload.get("aud") != JWT_AUDIENCE:
            raise ValueError("issuer or audience mismatch")
        if payload.get("typ", "access") != expected_type:
            raise ValueError("wrong token type")
        if int(payload.get("nbf", 0)) > now:
            raise ValueError("token not yet valid")
        if int(payload.get("exp", 0)) < now:
            raise ValueError("token expired")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc


@dataclass(frozen=True)
class Principal:
    subject: str
    device_id: str | None
    scopes: list[str]
    token_id: str | None = None


def optional_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization:
        if AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="missing bearer token")
        return Principal(subject="local-dev", device_id=None, scopes=["*"], token_id=None)
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization header")
    payload = verify_token(token)
    return Principal(
        subject=str(payload.get("sub")),
        device_id=payload.get("device_id"),
        scopes=list(payload.get("scopes", [])),
        token_id=payload.get("jti"),
    )


def require_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing bearer token")
    return optional_principal(authorization)


def require_scope(principal: Principal, scope: str) -> None:
    if "*" not in principal.scopes and scope not in principal.scopes:
        raise HTTPException(status_code=403, detail=f"missing scope: {scope}")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization header")
    return token
