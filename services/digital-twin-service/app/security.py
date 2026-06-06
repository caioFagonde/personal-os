from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() == "true"

@dataclass(frozen=True)
class Principal:
    subject: str
    device_id: str | None
    scopes: list[str]
    token_id: str | None = None


def optional_principal(authorization: str | None = None) -> Principal:
    if not AUTH_REQUIRED:
        return Principal(
            subject="local-dev",
            device_id="local-dev",
            scopes=[
                "digital_twin:read",
                "digital_twin:write",
                "recommendations:write",
                "digital_twin:export",
                "automation:write",
            ],
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="invalid token")
    payload = _decode_json(parts[1])
    return Principal(
        subject=str(payload.get("sub", "")),
        device_id=payload.get("device_id"),
        scopes=list(payload.get("scopes", [])),
        token_id=payload.get("jti"),
    )


def require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes and "admin" not in principal.scopes:
        raise HTTPException(status_code=403, detail=f"missing scope: {scope}")


def _decode_json(part: str) -> dict[str, Any]:
    padding = "=" * (-len(part) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(part + padding))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token payload") from exc
