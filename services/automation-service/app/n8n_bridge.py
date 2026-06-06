from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WebhookEnvelope:
    source: str
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sign_payload(payload: dict[str, Any], secret: str, *, timestamp: int | None = None) -> str:
    ts = timestamp or int(time.time())
    message = f"{ts}.{canonical_json(payload)}"
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def verify_payload_signature(payload: dict[str, Any], signature: str, secret: str, *, tolerance_seconds: int = 300, now: int | None = None) -> bool:
    parts = dict(part.split("=", 1) for part in signature.split(",") if "=" in part)
    try:
        ts = int(parts.get("t", "0"))
    except ValueError:
        return False
    now = now or int(time.time())
    if abs(now - ts) > tolerance_seconds:
        return False
    expected = sign_payload(payload, secret, timestamp=ts)
    return hmac.compare_digest(expected, signature)


def normalize_n8n_webhook(payload: dict[str, Any], *, source: str = "n8n") -> WebhookEnvelope:
    event_type = str(payload.get("event") or payload.get("type") or "n8n.webhook")
    key_material = canonical_json({"source": source, "event_type": event_type, "payload": payload})
    return WebhookEnvelope(
        source=source,
        event_type=event_type,
        payload=payload,
        idempotency_key=hashlib.sha256(key_material.encode()).hexdigest(),
    )
