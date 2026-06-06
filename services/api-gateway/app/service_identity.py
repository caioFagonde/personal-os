from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

SERVICE_ISSUER = os.environ.get("SERVICE_TOKEN_ISSUER", "personal-os-control-plane")
SERVICE_AUDIENCE = os.environ.get("SERVICE_TOKEN_AUDIENCE", "personal-os-internal")
SERVICE_TOKEN_SECRET = os.environ.get("SERVICE_TOKEN_SECRET", os.environ.get("JWT_SECRET", "local-dev-only-change-me"))
SERVICE_TOKEN_TTL_SECONDS = int(os.environ.get("SERVICE_TOKEN_TTL_SECONDS", "300"))


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class ServicePrincipal:
    service: str
    scopes: tuple[str, ...]
    expires_at: int


def issue_service_token(service: str, scopes: list[str], *, ttl_seconds: int | None = None, issued_at: int | None = None) -> str:
    if not service or any(ch.isspace() for ch in service):
        raise ValueError("service must be a non-empty token without whitespace")
    now = int(issued_at if issued_at is not None else time.time())
    ttl = ttl_seconds if ttl_seconds is not None else SERVICE_TOKEN_TTL_SECONDS
    if ttl <= 0 or ttl > 3600:
        raise ValueError("service token ttl must be between 1 and 3600 seconds")
    header = {"alg": "HS256", "typ": "PST", "kid": "service-v1"}
    payload = {
        "iss": SERVICE_ISSUER,
        "aud": SERVICE_AUDIENCE,
        "sub": service,
        "scopes": sorted(set(scopes)),
        "iat": now,
        "nbf": now - 5,
        "exp": now + ttl,
    }
    signing_input = f"{_b64e(_canonical_json(header).encode())}.{_b64e(_canonical_json(payload).encode())}"
    signature = hmac.new(SERVICE_TOKEN_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64e(signature)}"


def verify_service_token(token: str, *, required_scope: str | None = None, now: int | None = None) -> ServicePrincipal:
    try:
        head, body, sig = token.split(".")
        header = json.loads(_b64d(head))
        payload = json.loads(_b64d(body))
        if header.get("alg") != "HS256" or header.get("typ") != "PST":
            raise ValueError("unsupported service token header")
        expected = _b64e(hmac.new(SERVICE_TOKEN_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature mismatch")
        current = int(now if now is not None else time.time())
        if payload.get("iss") != SERVICE_ISSUER or payload.get("aud") != SERVICE_AUDIENCE:
            raise ValueError("issuer or audience mismatch")
        if int(payload.get("nbf", 0)) > current or int(payload.get("exp", 0)) < current:
            raise ValueError("service token expired or not yet valid")
        scopes = tuple(payload.get("scopes", []))
        if required_scope and required_scope not in scopes and "*" not in scopes:
            raise PermissionError(f"missing service scope: {required_scope}")
        return ServicePrincipal(service=str(payload["sub"]), scopes=scopes, expires_at=int(payload["exp"]))
    except PermissionError:
        raise
    except Exception as exc:
        raise ValueError("invalid service token") from exc


def service_auth_header(service: str, scopes: list[str]) -> dict[str, str]:
    return {"x-personal-os-service-token": issue_service_token(service, scopes)}
