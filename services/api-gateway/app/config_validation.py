from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException

SECRET_MARKERS = ("SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY", "API_KEY", "AUTH_KEY", "CREDENTIAL")
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def is_sensitive_key(key: str) -> bool:
    return any(marker in key.upper() for marker in SECRET_MARKERS)


def public_setting(key: str, value: Any) -> Any:
    if is_sensitive_key(key) and value not in (None, ""):
        return {"configured": True, "masked": "********"}
    return value


def validate_setting(key: str, value: Any) -> None:
    if value in (None, "") or not isinstance(value, str):
        return
    upper = key.upper()
    message: str | None = None
    if upper.endswith("_PORT"):
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            message = "must be an integer from 1 to 65535"
    elif "TWILIO" in upper and "WHATSAPP" in upper and ("FROM" in upper or "SENDER" in upper):
        if not value.startswith("whatsapp:") or not PHONE_RE.fullmatch(value.removeprefix("whatsapp:")):
            message = "must use whatsapp:+<E.164 number> format"
    elif "PHONE" in upper and not PHONE_RE.fullmatch(value):
        message = "must be an E.164 phone number"
    elif upper.endswith(("_URL", "_URI", "_ENDPOINT")):
        try:
            parsed = urlparse(value)
            parsed.port
        except ValueError:
            parsed = None
            message = "must be a valid URL"
        if not message and (parsed is None or parsed.scheme not in {"http", "https"} or not parsed.hostname):
            message = "must be an absolute http:// or https:// URL"
        if not message and "REDIRECT_URI" in upper and parsed and parsed.fragment:
            message = "OAuth redirect URI must not contain a fragment"
    if message:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_config", "field": key, "message": message, "setup_path": "/settings"},
        )
