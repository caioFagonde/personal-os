"""Obsidian vault markdown schema (Phase D1) — pure functions, no I/O.

Renders and parses the Dataview-compatible frontmatter, Obsidian-Tasks-
compatible task lines, guarded blocks, wikilinks, and per-kind notes defined
in OBSIDIAN_INTEGRATION_SPEC.md. Everything here is deterministic and
side-effect free so it can be golden-file tested.
"""
from __future__ import annotations

import json
import re
from typing import Any

import yaml

FRONTMATTER_MAX_BYTES = 32_768
NEXUS_TAG = "nexus"

# Obsidian Tasks plugin priority emoji, keyed by tasks.priority (1 highest).
PRIORITY_EMOJI = {1: "🔺", 2: "⏫", 4: "🔽", 5: "⏬"}
EMOJI_PRIORITY = {v: k for k, v in PRIORITY_EMOJI.items()}

TASK_LINE_RE = re.compile(
    r"^- \[(?P<done>[ xX])\] (?P<text>.*?)\s*\[nexus:: task/(?P<id>[0-9a-fA-F-]{36})\]\s*$"
)
DUE_RE = re.compile(r"📅 (\d{4}-\d{2}-\d{2})")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
GUARD_START = "<!-- nexus:{name}:start -->"
GUARD_END = "<!-- nexus:{name}:end -->"

# Deterministic frontmatter key order: identity first, then lifecycle, then extras.
_KEY_ORDER = ["nexus_id", "nexus_kind", "nexus_rev", "status", "tags", "created", "updated", "aliases", "day"]


# --- frontmatter ---------------------------------------------------------------

def render_frontmatter(fields: dict[str, Any]) -> str:
    ordered: dict[str, Any] = {}
    for key in _KEY_ORDER:
        if key in fields:
            ordered[key] = fields[key]
    for key in sorted(k for k in fields if k not in _KEY_ORDER):
        ordered[key] = fields[key]
    dumped = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=None).strip()
    return f"---\n{dumped}\n---\n"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (fields, body). Missing/oversized/malformed frontmatter → ({}, text)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    raw = text[4:end]
    if len(raw.encode("utf-8")) > FRONTMATTER_MAX_BYTES:
        return {}, text
    try:
        fields = yaml.safe_load(raw)  # safe_load only — never full YAML
    except yaml.YAMLError:
        return {}, text
    if not isinstance(fields, dict):
        return {}, text
    body = text[end + 4:]
    if body.startswith("\n"):
        body = body[1:]
    return fields, body


# --- task lines ------------------------------------------------------------------

def render_task_line(task: dict[str, Any]) -> str:
    done = task.get("status") == "completed"
    parts = [f"- [{'x' if done else ' '}] {task['title']}"]
    due = task.get("due_at")
    if due:
        parts.append(f"📅 {str(due)[:10]}")
    emoji = PRIORITY_EMOJI.get(int(task.get("priority") or 3))
    if emoji:
        parts.append(emoji)
    parts.append(f"[nexus:: task/{task['id']}]")
    return " ".join(parts)


def parse_task_lines(body: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for line in body.splitlines():
        match = TASK_LINE_RE.match(line.strip())
        if not match:
            continue
        text = match.group("text").strip()
        due = None
        due_match = DUE_RE.search(text)
        if due_match:
            due = due_match.group(1)
        priority = 3
        for emoji, rank in EMOJI_PRIORITY.items():
            if emoji in text:
                priority = rank
                break
        title = DUE_RE.sub("", text)
        for emoji in PRIORITY_EMOJI.values():
            title = title.replace(emoji, "")
        tasks.append({
            "id": match.group("id").lower(),
            "done": match.group("done").lower() == "x",
            "title": title.strip(),
            "due": due,
            "priority": priority,
        })
    return tasks


# --- guarded blocks -----------------------------------------------------------------

def render_guard_block(name: str, content: str) -> str:
    return f"{GUARD_START.format(name=name)}\n{content.rstrip()}\n{GUARD_END.format(name=name)}"


def replace_guard_block(body: str, name: str, content: str) -> str:
    """Replace the named guarded block, or append it; user text outside survives."""
    start, end = GUARD_START.format(name=name), GUARD_END.format(name=name)
    block = render_guard_block(name, content)
    if start in body and end in body:
        pre = body.split(start, 1)[0]
        post = body.split(end, 1)[1]
        return f"{pre}{block}{post}"
    suffix = "" if body.endswith("\n") else "\n"
    return f"{body}{suffix}\n{block}\n" if body.strip() else f"{block}\n"


def extract_guard_block(body: str, name: str) -> str | None:
    start, end = GUARD_START.format(name=name), GUARD_END.format(name=name)
    if start not in body or end not in body:
        return None
    inner = body.split(start, 1)[1].split(end, 1)[0]
    return inner.strip("\n")


# --- wikilinks ---------------------------------------------------------------------

def extract_wikilinks(body: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in WIKILINK_RE.finditer(body):
        seen.setdefault(match.group(1).strip(), None)
    return list(seen)


# --- per-kind renderers ---------------------------------------------------------------

def _base_fields(obj: dict[str, Any], kind: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "nexus_id": str(obj["nexus_id"]),
        "nexus_kind": kind,
        "nexus_rev": str(obj.get("rev") or ""),
        "tags": [NEXUS_TAG, kind, *[t for t in obj.get("tags") or [] if t not in (NEXUS_TAG, kind)]],
    }
    if obj.get("status"):
        fields["status"] = obj["status"]
    if obj.get("created_at"):
        fields["created"] = str(obj["created_at"])[:10]
    if obj.get("updated_at"):
        fields["updated"] = str(obj["updated_at"])
    fields["aliases"] = obj.get("aliases") or []
    return fields


def render_related_footer(related: list[str]) -> str:
    lines = "\n".join(f"- [[{target}]]" for target in related)
    return f"## Related\n{lines}" if related else "## Related\n_(none)_"


def render_project_readme(project: dict[str, Any], tasks: list[dict[str, Any]], related: list[str]) -> str:
    fields = _base_fields(project, "project")
    fm = render_frontmatter(fields)
    task_lines = "\n".join(render_task_line(t) for t in tasks) or "_(no open tasks)_"
    body = (
        f"# {project['name']}\n\n"
        f"{project.get('pitch') or ''}\n\n"
        f"**North star:** {project.get('north_star') or '—'}\n\n"
        f"## Tasks\n{render_guard_block('tasks', task_lines)}\n\n"
        f"{render_guard_block('related', render_related_footer(related))}\n"
    )
    return fm + body


def render_daily_note(daily: dict[str, Any], focus_tasks: list[dict[str, Any]], log_lines: list[str]) -> str:
    fields = _base_fields(daily, "daily_state")
    fields["day"] = str(daily["day"])
    fm = render_frontmatter(fields)
    tasks = "\n".join(render_task_line(t) for t in focus_tasks) or "_(none)_"
    log = "\n".join(f"- {line}" for line in log_lines) or "_(quiet day so far)_"
    body = (
        f"## Intention\n{daily.get('intention') or ''}\n\n"
        f"## Focus\n{render_guard_block('focus', tasks)}\n\n"
        f"## Log\n{render_guard_block('log', log)}\n\n"
        f"## Review\n{daily.get('review') or ''}\n"
    )
    return fm + body


def render_decision_note(decision: dict[str, Any]) -> str:
    fields = _base_fields(decision, "decision")
    fields["decision_status"] = decision.get("status", "accepted")
    fm = render_frontmatter(fields)
    body = (
        f"# {decision['title']}\n\n"
        f"## Context\n{decision.get('context') or ''}\n\n"
        f"## Decision\n{decision.get('decision') or ''}\n\n"
        f"## Consequences\n{decision.get('consequences') or ''}\n"
    )
    return fm + body


def render_zettel_note(note: dict[str, Any], related: list[str]) -> str:
    fields = _base_fields(note, "note")
    fm = render_frontmatter(fields)
    body = f"# {note['title']}\n\n{note.get('body') or ''}\n\n{render_guard_block('related', render_related_footer(related))}\n"
    return fm + body


# --- daily sections (inbound parsing) ----------------------------------------------------

SECTION_RE = re.compile(r"^## (Intention|Focus|Log|Review)\s*$", re.MULTILINE)


def parse_daily_sections(body: str) -> dict[str, str]:
    """Split a daily note body into its four sections (guard blocks stripped)."""
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(body))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        name = match.group(1).lower()
        content = body[start:end].strip("\n")
        # strip guard markers so user prose is what remains
        content = re.sub(r"<!-- nexus:[a-z]+:(start|end) -->", "", content).strip()
        sections[name] = content
    return sections


# --- canvas export ----------------------------------------------------------------------

def render_canvas(project: dict[str, Any], nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    """Emit Obsidian .canvas JSON: file nodes laid out on a simple grid.

    nodes: [{id, file}] — vault-relative markdown paths.
    edges: [{src, dst, rel}] — node ids.
    """
    canvas_nodes = []
    for i, node in enumerate(nodes):
        canvas_nodes.append({
            "id": node["id"],
            "type": "file",
            "file": node["file"],
            "x": (i % 4) * 460,
            "y": (i // 4) * 260,
            "width": 400,
            "height": 200,
        })
    canvas_edges = [
        {"id": f"e{i}", "fromNode": e["src"], "toNode": e["dst"], "label": e.get("rel", "")}
        for i, e in enumerate(edges)
    ]
    return json.dumps(
        {
            "nodes": canvas_nodes,
            "edges": canvas_edges,
            # guard note: regenerated on demand, never merged
            "metadata": {"generator": "nexus", "project": project.get("slug", ""), "machine_generated": True},
        },
        indent=2,
        ensure_ascii=False,
    )
