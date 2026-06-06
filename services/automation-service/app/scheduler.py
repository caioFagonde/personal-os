from __future__ import annotations

from datetime import datetime, timedelta, timezone


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def next_interval_due(last_run_at: datetime | None, every_seconds: int, *, now: datetime | None = None) -> datetime:
    now = normalize_utc(now or datetime.now(timezone.utc))
    if last_run_at is None:
        return now
    return normalize_utc(last_run_at) + timedelta(seconds=every_seconds)


def is_interval_due(last_run_at: datetime | None, every_seconds: int, *, now: datetime | None = None) -> bool:
    now = normalize_utc(now or datetime.now(timezone.utc))
    return next_interval_due(last_run_at, every_seconds, now=now) <= now


def stable_jitter_seconds(key: str, maximum: int) -> int:
    if maximum <= 0:
        return 0
    total = sum(ord(ch) for ch in key)
    return total % (maximum + 1)
