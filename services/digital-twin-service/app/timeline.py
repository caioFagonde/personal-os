from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from .ontology import infer_domains


def event_id(event_type: str, occurred_at: datetime, source: str, payload: dict[str, Any]) -> str:
    basis = f"{event_type}|{occurred_at.isoformat()}|{source}|{payload}"
    return sha256(basis.encode()).hexdigest()[:32]


def normalize_event(event_type: str, payload: dict[str, Any] | None = None, occurred_at: datetime | None = None, source: str = "manual") -> dict[str, Any]:
    occurred_at = occurred_at or datetime.now(timezone.utc)
    payload = payload or {}
    domains = infer_domains(event_type, payload)
    importance = float(payload.get("importance", 0.5))
    importance = min(1.0, max(0.0, importance))
    return {
        "event_uid": event_id(event_type, occurred_at, source, payload),
        "event_type": event_type,
        "source": source,
        "domains": domains,
        "importance": importance,
        "occurred_at": occurred_at,
        "payload": payload,
    }


def aggregate_timeline(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    importance_sum = 0.0
    dates: list[datetime] = []
    for event in events:
        for domain in event.get("domains", []) or []:
            by_domain[domain] += 1
        by_type[event.get("event_type", "unknown")] += 1
        importance_sum += float(event.get("importance", 0.0))
        occurred = event.get("occurred_at")
        if isinstance(occurred, datetime):
            dates.append(occurred)
    return {
        "event_count": len(events),
        "domain_counts": dict(by_domain),
        "event_type_counts": dict(by_type),
        "importance_avg": round(importance_sum / len(events), 4) if events else 0.0,
        "first_event_at": min(dates).isoformat() if dates else None,
        "last_event_at": max(dates).isoformat() if dates else None,
    }


def infer_state_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    aggregation = aggregate_timeline(events)
    domain_counts = aggregation["domain_counts"]
    total = max(1, aggregation["event_count"])
    focus_distribution = {domain: round(count / total, 4) for domain, count in sorted(domain_counts.items())}
    health_load = domain_counts.get("health", 0) + domain_counts.get("mindfulness", 0)
    learning_load = domain_counts.get("learning", 0) + domain_counts.get("knowledge", 0) + domain_counts.get("research", 0)
    ops_load = domain_counts.get("automation", 0) + domain_counts.get("operations", 0)
    return {
        "focus_distribution": focus_distribution,
        "learning_momentum": min(1.0, learning_load / 7.0),
        "recovery_pressure": min(1.0, health_load / 5.0),
        "ops_pressure": min(1.0, ops_load / 4.0),
        "confidence": min(1.0, total / 10.0),
    }
