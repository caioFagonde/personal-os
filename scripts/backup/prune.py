"""Backup retention policy (Phase E4) — pure functions.

Grandfather-father-son: keep the last N daily, M weekly, K monthly snapshots.
Hard safety rule: NEVER delete the only verified copy, even if policy says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Snapshot:
    backup_id: str
    created_at: datetime
    verified: bool


DEFAULT_KEEP_DAILY = 7
DEFAULT_KEEP_WEEKLY = 4
DEFAULT_KEEP_MONTHLY = 6


def _iso_week(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return (iso[0], iso[1])


def select_keep(
    snapshots: list[Snapshot],
    *,
    keep_daily: int = DEFAULT_KEEP_DAILY,
    keep_weekly: int = DEFAULT_KEEP_WEEKLY,
    keep_monthly: int = DEFAULT_KEEP_MONTHLY,
) -> set[str]:
    """Return the set of backup_ids to KEEP. Newest snapshot in each bucket wins."""
    ordered = sorted(snapshots, key=lambda s: s.created_at, reverse=True)
    keep: set[str] = set()

    # Daily: newest snapshot of each of the most recent `keep_daily` days.
    seen_days: list[date] = []
    for snap in ordered:
        day = snap.created_at.date()
        if day not in seen_days and len(seen_days) < keep_daily:
            seen_days.append(day)
            keep.add(snap.backup_id)

    # Weekly: newest snapshot per ISO week, up to `keep_weekly` weeks.
    seen_weeks: list[tuple[int, int]] = []
    for snap in ordered:
        wk = _iso_week(snap.created_at.date())
        if wk not in seen_weeks:
            if len(seen_weeks) < keep_weekly:
                seen_weeks.append(wk)
                keep.add(snap.backup_id)

    # Monthly: newest snapshot per (year, month), up to `keep_monthly` months.
    seen_months: list[tuple[int, int]] = []
    for snap in ordered:
        mo = (snap.created_at.year, snap.created_at.month)
        if mo not in seen_months:
            if len(seen_months) < keep_monthly:
                seen_months.append(mo)
                keep.add(snap.backup_id)

    return keep


def plan_prune(
    snapshots: list[Snapshot],
    *,
    keep_daily: int = DEFAULT_KEEP_DAILY,
    keep_weekly: int = DEFAULT_KEEP_WEEKLY,
    keep_monthly: int = DEFAULT_KEEP_MONTHLY,
) -> tuple[list[str], list[str]]:
    """Return (keep_ids, delete_ids). Never deletes the only verified copy."""
    keep = select_keep(snapshots, keep_daily=keep_daily, keep_weekly=keep_weekly, keep_monthly=keep_monthly)
    delete = [s.backup_id for s in snapshots if s.backup_id not in keep]

    verified_ids = {s.backup_id for s in snapshots if s.verified}
    verified_kept = verified_ids & keep
    if verified_ids and not verified_kept:
        # Policy would drop every verified copy — rescue the newest verified one.
        newest_verified = max(
            (s for s in snapshots if s.verified), key=lambda s: s.created_at
        )
        keep.add(newest_verified.backup_id)
        delete = [bid for bid in delete if bid != newest_verified.backup_id]

    return sorted(keep), sorted(delete)
