"""Three-way merge for vault sync (Phase D2) — pure functions, no deps.

Fields merge per key; bodies merge with a diff3-style line algorithm built on
difflib. When both sides changed the same region differently the result is a
conflict: fields report the key, bodies get git-style conflict markers and the
caller records a vault conflict instead of writing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

APP_MARKER = "<<<<<<< app"
SEP_MARKER = "======="
VAULT_MARKER = ">>>>>>> vault"


@dataclass
class FieldMerge:
    merged: dict[str, Any]
    conflicts: list[str] = field(default_factory=list)


def merge_fields(base: dict[str, Any], local: dict[str, Any], remote: dict[str, Any]) -> FieldMerge:
    """local = app state, remote = vault state, base = last synced snapshot."""
    merged: dict[str, Any] = {}
    conflicts: list[str] = []
    for key in dict.fromkeys([*base, *local, *remote]):
        base_v, app_v, vault_v = base.get(key), local.get(key), remote.get(key)
        if app_v == vault_v:
            value = app_v
        elif app_v == base_v:
            value = vault_v  # only the vault changed it
        elif vault_v == base_v:
            value = app_v  # only the app changed it
        else:
            conflicts.append(key)
            value = app_v  # app wins provisionally; caller surfaces the conflict
        if value is not None:
            merged[key] = value
    return FieldMerge(merged=merged, conflicts=conflicts)


@dataclass
class BodyMerge:
    merged: str
    conflict: bool


def _changed_regions(base: list[str], side: list[str]) -> list[tuple[int, int, list[str]]]:
    """Regions of `base` replaced by `side`: (base_start, base_end, replacement)."""
    regions = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=base, b=side, autojunk=False).get_opcodes():
        if tag != "equal":
            regions.append((i1, i2, side[j1:j2]))
    return regions


def _render_side(
    base_lines: list[str],
    group: list[tuple[int, int, str, list[str]]],
    side: str,
    start: int,
    end: int,
) -> list[str]:
    """Render one side's version of base[start:end] with its replacements applied."""
    regions = sorted((g for g in group if g[2] == side), key=lambda g: g[0])
    out: list[str] = []
    pos = start
    for region_start, region_end, _, replacement in regions:
        out.extend(base_lines[pos:region_start])
        out.extend(replacement)
        pos = max(pos, region_end)
    out.extend(base_lines[pos:end])
    return out


def merge_bodies(base: str, local: str, remote: str) -> BodyMerge:
    if local == remote or remote == base:
        return BodyMerge(merged=local, conflict=False)
    if local == base:
        return BodyMerge(merged=remote, conflict=False)

    base_lines = base.splitlines()
    local_regions = _changed_regions(base_lines, local.splitlines())
    remote_regions = _changed_regions(base_lines, remote.splitlines())

    # Merge the two region lists over base coordinates.
    events: list[tuple[int, int, str, list[str]]] = [
        (*r[:2], "local", r[2]) for r in local_regions
    ] + [(*r[:2], "remote", r[2]) for r in remote_regions]
    events.sort(key=lambda e: (e[0], e[1]))

    merged: list[str] = []
    conflict = False
    cursor = 0
    i = 0
    while i < len(events):
        start, end, side, replacement = events[i]
        # Coalesce every event whose base range touches the group's range.
        # Pure insertions (start == end) at the group boundary count as touching.
        group = [(start, end, side, replacement)]
        group_end = max(end, start)
        j = i + 1
        while j < len(events) and events[j][0] <= group_end:
            group.append(events[j])
            group_end = max(group_end, events[j][1])
            j += 1
        merged.extend(base_lines[cursor:start])
        cursor = max(group_end, start)

        sides = {g[2] for g in group}
        local_text = _render_side(base_lines, group, "local", start, group_end)
        remote_text = _render_side(base_lines, group, "remote", start, group_end)
        if sides == {"local"}:
            merged.extend(local_text)
        elif sides == {"remote"}:
            merged.extend(remote_text)
        elif local_text == remote_text:
            merged.extend(local_text)
        else:
            conflict = True
            merged.append(APP_MARKER)
            merged.extend(local_text)
            merged.append(SEP_MARKER)
            merged.extend(remote_text)
            merged.append(VAULT_MARKER)
        i = j

    merged.extend(base_lines[cursor:])
    trailing = "\n" if (local.endswith("\n") or remote.endswith("\n")) else ""
    return BodyMerge(merged="\n".join(merged) + trailing, conflict=conflict)
