from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

SENSITIVITY_RANK = {"public": 0, "personal": 1, "sensitive": 2, "restricted": 3}
MEMORY_CLASSES = {"ephemeral", "working", "long_term", "archival"}
PURPOSE_SCOPES = {
    "recommendation": {"digital_twin:read", "recommendations:write"},
    "search": {"digital_twin:read"},
    "export": {"digital_twin:export"},
    "automation": {"digital_twin:read", "automation:write"},
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
TOKEN_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+")

DEFAULT_POLICY = {
    "ephemeral_days": 7,
    "working_days": 90,
    "long_term_days": 3650,
    "allow_sensitive_recommendations": False,
    "allow_restricted_export": False,
    "redact_external_outputs": True,
}


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_POLICY)
    if policy:
        merged.update({k: v for k, v in policy.items() if v is not None})
    return merged


def classify_sensitivity(text: str | None = None, declared: str | None = None, tags: list[str] | None = None) -> str:
    if declared in SENSITIVITY_RANK:
        return declared
    tags = [t.lower() for t in (tags or [])]
    if any(t in {"medical", "health", "location", "financial", "credential"} for t in tags):
        return "sensitive"
    text = text or ""
    if TOKEN_RE.search(text):
        return "restricted"
    if EMAIL_RE.search(text) or PHONE_RE.search(text):
        return "personal"
    return "personal" if text.strip() else "public"


def redact_text(text: str, *, external: bool = True) -> str:
    if not external:
        return text
    text = TOKEN_RE.sub(lambda m: m.group(1) + "=<redacted>", text)
    text = EMAIL_RE.sub("<email>", text)
    text = PHONE_RE.sub("<phone>", text)
    return text


def retention_deadline(memory_class: str, created_at: datetime, policy: dict[str, Any] | None = None) -> datetime | None:
    p = normalize_policy(policy)
    if memory_class == "archival":
        return None
    if memory_class == "long_term":
        return created_at + timedelta(days=int(p["long_term_days"]))
    if memory_class == "working":
        return created_at + timedelta(days=int(p["working_days"]))
    return created_at + timedelta(days=int(p["ephemeral_days"]))


def is_expired(memory_class: str, created_at: datetime, now: datetime | None = None, policy: dict[str, Any] | None = None) -> bool:
    deadline = retention_deadline(memory_class, created_at, policy)
    if deadline is None:
        return False
    now = now or datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now > deadline


def allowed_for_purpose(scopes: set[str], purpose: str, sensitivity: str, policy: dict[str, Any] | None = None) -> tuple[bool, str]:
    p = normalize_policy(policy)
    required = PURPOSE_SCOPES.get(purpose, {"digital_twin:read"})
    if not required <= scopes:
        return False, f"missing scopes: {sorted(required - scopes)}"
    if sensitivity == "restricted" and purpose == "export" and not p["allow_restricted_export"]:
        return False, "restricted memories require explicit export override"
    if sensitivity in {"sensitive", "restricted"} and purpose == "recommendation" and not p["allow_sensitive_recommendations"]:
        return False, "sensitive memories are excluded from recommendations by policy"
    return True, "allowed"


def sanitize_memory_record(record: dict[str, Any], policy: dict[str, Any] | None = None, *, external: bool = True) -> dict[str, Any]:
    p = normalize_policy(policy)
    out = dict(record)
    if p["redact_external_outputs"]:
        for key in ("content", "summary", "rationale"):
            if isinstance(out.get(key), str):
                out[key] = redact_text(out[key], external=external)
    return out
