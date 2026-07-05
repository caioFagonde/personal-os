"""Golden tests for the vault markdown schema (pure functions)."""
from app.vault_schema import (
    extract_guard_block,
    extract_wikilinks,
    parse_daily_sections,
    parse_frontmatter,
    parse_task_lines,
    render_canvas,
    render_daily_note,
    render_decision_note,
    render_frontmatter,
    render_project_readme,
    render_task_line,
    render_zettel_note,
    replace_guard_block,
)

TASK = {"id": "018f3c00-0000-4000-8000-000000000001", "title": "Ship vault indexer", "status": "inbox", "due_at": "2026-07-10", "priority": 2}
PROJECT = {"nexus_id": "018f3c00-0000-4000-8000-00000000000a", "name": "Nexus Prime", "slug": "nexus-prime",
           "pitch": "A sovereign personal OS.", "north_star": "Daily driver.", "status": "active",
           "created_at": "2026-07-01", "updated_at": "2026-07-03T10:00:00Z", "rev": "r1"}


def test_frontmatter_round_trip():
    fm = render_frontmatter({"nexus_id": "abc", "nexus_kind": "note", "status": "permanent", "tags": ["nexus", "note"]})
    fields, body = parse_frontmatter(fm + "Body text")
    assert fields["nexus_id"] == "abc"
    assert fields["nexus_kind"] == "note"
    assert body == "Body text"
    # identity keys render first (stable diffs in the vault)
    lines = fm.splitlines()
    assert lines[1].startswith("nexus_id:")
    assert lines[2].startswith("nexus_kind:")


def test_frontmatter_is_safe_and_bounded():
    fields, body = parse_frontmatter("---\n" + "x: " + "a" * 40_000 + "\n---\nbody")
    assert fields == {}  # oversized → treated as plain body, never parsed
    fields2, _ = parse_frontmatter("---\n!!python/object:os.system []\n---\nbody")
    assert fields2 == {}  # unsafe YAML rejected by safe_load


def test_task_line_round_trip_golden():
    line = render_task_line(TASK)
    assert line == "- [ ] Ship vault indexer 📅 2026-07-10 ⏫ [nexus:: task/018f3c00-0000-4000-8000-000000000001]"
    parsed = parse_task_lines(line)[0]
    assert parsed == {"id": TASK["id"], "done": False, "title": "Ship vault indexer", "due": "2026-07-10", "priority": 2}


def test_completed_task_renders_checked():
    line = render_task_line({**TASK, "status": "completed"})
    assert line.startswith("- [x]")
    assert parse_task_lines(line)[0]["done"] is True


def test_guard_blocks_preserve_user_prose():
    body = replace_guard_block("My own thoughts.\n", "tasks", "- [ ] one")
    updated = replace_guard_block(body, "tasks", "- [ ] two")
    assert "My own thoughts." in updated
    assert extract_guard_block(updated, "tasks") == "- [ ] two"
    assert "- [ ] one" not in updated


def test_project_readme_golden_shape():
    md = render_project_readme(PROJECT, [TASK], ["Notes/related-note"])
    fields, body = parse_frontmatter(md)
    assert fields["nexus_kind"] == "project"
    assert "# Nexus Prime" in body
    assert "<!-- nexus:tasks:start -->" in body
    assert "[[Notes/related-note]]" in body
    assert parse_task_lines(body)[0]["id"] == TASK["id"]


def test_daily_note_sections_round_trip():
    daily = {"nexus_id": "x", "day": "2026-07-03", "intention": "Ship Phase D", "review": "", "rev": "r"}
    md = render_daily_note(daily, [TASK], ["captured: something"])
    _, body = parse_frontmatter(md)
    sections = parse_daily_sections(body)
    assert sections["intention"] == "Ship Phase D"
    assert "Ship vault indexer" in sections["focus"]


def test_decision_note_carries_status():
    md = render_decision_note({"nexus_id": "d", "title": "Use pgvector", "context": "ctx", "decision": "yes",
                               "consequences": "none", "status": "accepted", "rev": "r"})
    fields, body = parse_frontmatter(md)
    assert fields["decision_status"] == "accepted"
    assert "## Consequences" in body


def test_zettel_note_and_wikilinks():
    md = render_zettel_note({"nexus_id": "n", "title": "CRDTs", "body": "See [[Vector Clocks]].", "rev": "r"}, [])
    _, body = parse_frontmatter(md)
    assert extract_wikilinks(body) == ["Vector Clocks"]


def test_canvas_is_machine_marked_json():
    import json
    canvas = json.loads(render_canvas({"slug": "nexus-prime"}, [{"id": "a", "file": "Projects/nexus-prime/README.md"}], []))
    assert canvas["metadata"]["machine_generated"] is True
    assert canvas["nodes"][0]["type"] == "file"
