from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VectorClock = dict[str, int]

def compare_clock(a: VectorClock, b: VectorClock) -> str:
    """Return 'before', 'after', 'equal', or 'concurrent'."""
    keys = set(a) | set(b)
    a_lt = any(a.get(k, 0) < b.get(k, 0) for k in keys)
    a_gt = any(a.get(k, 0) > b.get(k, 0) for k in keys)
    if a_lt and not a_gt:
        return 'before'
    if a_gt and not a_lt:
        return 'after'
    if not a_lt and not a_gt:
        return 'equal'
    return 'concurrent'

def merge_lww(local: dict[str, Any], remote: dict[str, Any], local_ts: str, remote_ts: str) -> dict[str, Any]:
    return remote if remote_ts >= local_ts else local

def merge_field(local: dict[str, Any], remote: dict[str, Any], local_changed: set[str], remote_changed: set[str]) -> tuple[dict[str, Any], list[str]]:
    merged = dict(local)
    conflicts: list[str] = []
    for key, value in remote.items():
        if key in local_changed and key in remote_changed and local.get(key) != value:
            conflicts.append(key)
            continue
        if key in remote_changed:
            merged[key] = value
    return merged, conflicts

def merge_set_union(local: list[Any], remote: list[Any]) -> list[Any]:
    seen = []
    for value in [*local, *remote]:
        if value not in seen:
            seen.append(value)
    return seen

@dataclass(frozen=True)
class SyncDecision:
    relation: str
    strategy: str
    needs_manual_resolution: bool

def decide_merge(local_clock: VectorClock, remote_clock: VectorClock, strategy: str) -> SyncDecision:
    relation = compare_clock(local_clock, remote_clock)
    return SyncDecision(
        relation=relation,
        strategy=strategy,
        needs_manual_resolution=(relation == 'concurrent' and strategy == 'manual'),
    )
