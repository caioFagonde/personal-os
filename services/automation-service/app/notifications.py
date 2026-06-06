from __future__ import annotations

from string import Template
from typing import Any


def render_template(template: str, data: dict[str, Any]) -> str:
    flat = {key: str(value) for key, value in data.items() if isinstance(key, str)}
    return Template(template).safe_substitute(flat)


def classify_notification_priority(priority: str | None) -> str:
    value = (priority or "default").lower()
    if value in {"min", "low", "default", "high", "urgent"}:
        return value
    return "default"


def build_notification(topic: str, title: str, message: str, *, priority: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    return {
        "topic": topic,
        "title": title[:160],
        "message": message[:4000],
        "priority": classify_notification_priority(priority),
        "tags": tags or [],
    }
