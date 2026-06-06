from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

VectorClock = dict[str, int]


def compare_clock(a: VectorClock, b: VectorClock) -> str:
    """Return 'before', 'after', 'equal', or 'concurrent'."""
    keys = set(a) | set(b)
    a_lt = any(a.get(k, 0) < b.get(k, 0) for k in keys)
    a_gt = any(a.get(k, 0) > b.get(k, 0) for k in keys)
    if a_lt and not a_gt:
        return "before"
    if a_gt and not a_lt:
        return "after"
    if not a_lt and not a_gt:
        return "equal"
    return "concurrent"


def merge_clocks(a: VectorClock, b: VectorClock) -> VectorClock:
    return {k: max(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b)}


def merge_lww(local: dict[str, Any], remote: dict[str, Any], local_ts: str | datetime, remote_ts: str | datetime) -> dict[str, Any]:
    return remote if str(remote_ts) >= str(local_ts) else local


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


def merge_crdt_text(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    """Minimal operation-log text CRDT.

    Payload shape:
      {"text": "current", "ops": [{"id":"device:seq", "type":"append", "value":"..."}]}

    This is intentionally simple for the MVP: append operations are sorted by id and
    de-duplicated. Rich-text CRDTs can replace this without changing sync_log.
    """
    ops_by_id: dict[str, dict[str, Any]] = {}
    for op in [*(local.get("ops") or []), *(remote.get("ops") or [])]:
        if isinstance(op, dict) and op.get("id"):
            ops_by_id[str(op["id"])] = op
    text = ""
    for op_id in sorted(ops_by_id):
        op = ops_by_id[op_id]
        if op.get("type") == "set":
            text = str(op.get("value", ""))
        elif op.get("type") == "append":
            text += str(op.get("value", ""))
    if not ops_by_id:
        text = remote.get("text", local.get("text", ""))
    merged = dict(local)
    merged.update(remote)
    merged["text"] = text
    merged["ops"] = [ops_by_id[k] for k in sorted(ops_by_id)]
    return merged


@dataclass(frozen=True)
class MergeResult:
    relation: str
    strategy: str
    payload: dict[str, Any]
    clock: VectorClock
    conflicts: list[str]
    needs_manual_resolution: bool


@dataclass(frozen=True)
class SyncDecision:
    relation: str
    strategy: str
    needs_manual_resolution: bool


def decide_merge(local_clock: VectorClock, remote_clock: VectorClock, strategy: str) -> SyncDecision:
    relation = compare_clock(local_clock, remote_clock)
    return SyncDecision(relation=relation, strategy=strategy, needs_manual_resolution=(relation == "concurrent" and strategy == "manual"))


def resolve_payload(local: dict[str, Any], remote: dict[str, Any], local_clock: VectorClock, remote_clock: VectorClock, strategy: str, local_changed: set[str] | None = None, remote_changed: set[str] | None = None) -> MergeResult:
    relation = compare_clock(local_clock, remote_clock)
    if relation in {"before", "equal"}:
        return MergeResult(relation, strategy, remote, merge_clocks(local_clock, remote_clock), [], False)
    if relation == "after":
        return MergeResult(relation, strategy, local, merge_clocks(local_clock, remote_clock), [], False)
    if strategy == "manual":
        return MergeResult(relation, strategy, local, merge_clocks(local_clock, remote_clock), ["__manual__"], True)
    if strategy == "lww":
        return MergeResult(relation, strategy, remote, merge_clocks(local_clock, remote_clock), [], False)
    if strategy == "field_merge":
        l_changed = local_changed or set(local.keys())
        r_changed = remote_changed or set(remote.keys())
        payload, conflicts = merge_field(local, remote, l_changed, r_changed)
        return MergeResult(relation, strategy, payload, merge_clocks(local_clock, remote_clock), conflicts, bool(conflicts))
    if strategy == "set_union":
        payload = dict(local)
        for key, value in remote.items():
            if isinstance(value, list) and isinstance(local.get(key), list):
                payload[key] = merge_set_union(local[key], value)
            else:
                payload[key] = value
        return MergeResult(relation, strategy, payload, merge_clocks(local_clock, remote_clock), [], False)
    if strategy == "counter":
        payload = dict(local)
        for key, value in remote.items():
            if isinstance(value, (int, float)) and isinstance(local.get(key), (int, float)):
                payload[key] = local[key] + value
            else:
                payload[key] = value
        return MergeResult(relation, strategy, payload, merge_clocks(local_clock, remote_clock), [], False)
    if strategy == "crdt_text":
        return MergeResult(relation, strategy, merge_crdt_text(local, remote), merge_clocks(local_clock, remote_clock), [], False)
    return MergeResult(relation, strategy, local, merge_clocks(local_clock, remote_clock), ["__unknown_strategy__"], True)
