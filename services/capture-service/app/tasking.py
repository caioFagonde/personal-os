from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PRIORITY_WEIGHTS = {"urgent": 1, "high": 2, "normal": 3, "low": 4}


@dataclass(frozen=True)
class TaskDefaults:
    follow_up_hours: int = 24
    default_priority: str = "normal"


def priority_to_rank(priority: str | None) -> int:
    return PRIORITY_WEIGHTS.get((priority or "normal").lower(), PRIORITY_WEIGHTS["normal"])


NON_DELEGATION_TARGETS = {"self", "me", "note", "task", "todo", "capture"}


def initial_task_status(target: str | None) -> str:
    if target and target not in NON_DELEGATION_TARGETS:
        return "delegated"
    return "inbox"


def follow_up_at(due_at: datetime | None, created_at: datetime | None = None, defaults: TaskDefaults | None = None) -> datetime:
    defaults = defaults or TaskDefaults()
    base = due_at or (created_at or datetime.now(timezone.utc))
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(hours=defaults.follow_up_hours)


def stable_task_fingerprint(source_kind: str, source_id: str | None, body: str) -> str:
    import hashlib

    material = f"{source_kind}:{source_id or ''}:{' '.join(body.lower().split())}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
