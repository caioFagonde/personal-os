"""Vault path mapping (Phase D2) — pure functions.

objects.slug is the authoritative source for vault paths (PERSONAL_GRAPH_SCHEMA
slug discipline). Only the configured roots are ever touched; `.obsidian/`
is always protected.
"""
from __future__ import annotations

import re

# Mapped roots (OBSIDIAN_INTEGRATION_SPEC path table).
SYNC_ROOTS = (
    "Projects", "Daily", "Tasks", "Notes", "Sources", "Decisions",
    "Agent Runs", "Artifacts", "People", "Portfolio",
)

PROTECTED_PREFIXES = (".obsidian/", ".obsidian\\")


def sanitize_slug(slug: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9À-ÿ _-]+", "-", (slug or "").strip()).strip("-")
    return cleaned[:120] or "untitled"


def vault_relpath(
    kind: str,
    slug: str,
    *,
    day: str | None = None,
    decided_at: str | None = None,
    project_slug: str | None = None,
    short_id: str | None = None,
) -> str:
    slug = sanitize_slug(slug)
    if kind == "project":
        return f"Projects/{slug}/README.md"
    if kind == "daily_state":
        return f"Daily/{day or slug}.md"
    if kind == "task":
        return f"Tasks/{slug}.md"
    if kind == "note":
        return f"Notes/{slug}.md"
    if kind == "source":
        return f"Sources/{slug}.md"
    if kind == "decision":
        return f"Decisions/{(decided_at or '')[:10]}-{slug}.md"
    if kind == "agent_run":
        return f"Agent Runs/{(decided_at or '')[:10]}-{short_id or slug}.md"
    if kind == "artifact":
        return f"Artifacts/{sanitize_slug(project_slug or 'unfiled')}/{slug}.md"
    if kind == "person":
        return f"People/{slug}.md"
    if kind == "portfolio_case":
        return f"Portfolio/{slug}.md"
    raise ValueError(f"kind {kind!r} has no vault mapping")


def canvas_relpath(project_slug: str) -> str:
    return f"Projects/{sanitize_slug(project_slug)}/map.canvas"


def _normalize(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def is_protected(relative_path: str) -> bool:
    normalized = _normalize(relative_path)
    return normalized.startswith(".obsidian/") or normalized == ".obsidian"


def is_under_sync_root(relative_path: str) -> bool:
    normalized = _normalize(relative_path)
    return any(normalized.startswith(f"{root}/") for root in SYNC_ROOTS)


def kind_for_relpath(relative_path: str) -> str | None:
    """Best-effort inverse mapping used when indexing unmapped vault files."""
    normalized = relative_path.replace("\\", "/")
    root = normalized.split("/", 1)[0] if "/" in normalized else ""
    return {
        "Projects": "project",
        "Daily": "daily_state",
        "Tasks": "task",
        "Notes": "note",
        "Sources": "source",
        "Decisions": "decision",
        "Agent Runs": "agent_run",
        "Artifacts": "artifact",
        "People": "person",
        "Portfolio": "portfolio_case",
    }.get(root)
