"""Merge matrix + path-safety tests for vault sync (pure functions)."""
import pytest

from app.vault_merge import merge_bodies, merge_fields
from app.vault_paths import (
    canvas_relpath,
    is_protected,
    is_under_sync_root,
    kind_for_relpath,
    sanitize_slug,
    vault_relpath,
)

BASE = "# Title\n\nline one\nline two\nline three\n"


# --- 3-way merge matrix -----------------------------------------------------------

def test_app_only_change_wins():
    local = BASE.replace("line two", "line two edited in app")
    result = merge_bodies(BASE, local, BASE)
    assert result.merged == local and not result.conflict


def test_vault_only_change_wins():
    remote = BASE.replace("line two", "line two edited in vault")
    result = merge_bodies(BASE, BASE, remote)
    assert result.merged == remote and not result.conflict


def test_both_compatible_changes_merge():
    local = BASE.replace("line one", "line one (app)")
    remote = BASE.replace("line three", "line three (vault)")
    result = merge_bodies(BASE, local, remote)
    assert "line one (app)" in result.merged
    assert "line three (vault)" in result.merged
    assert not result.conflict


def test_both_conflicting_changes_flag_conflict_with_markers():
    local = BASE.replace("line two", "app version")
    remote = BASE.replace("line two", "vault version")
    result = merge_bodies(BASE, local, remote)
    assert result.conflict
    assert "<<<<<<< app" in result.merged
    assert "app version" in result.merged
    assert "vault version" in result.merged
    assert ">>>>>>> vault" in result.merged


def test_identical_changes_are_not_conflicts():
    changed = BASE.replace("line two", "same edit")
    result = merge_bodies(BASE, changed, changed)
    assert result.merged == changed and not result.conflict


def test_field_merge_matrix():
    base = {"status": "active", "tags": ["a"]}
    assert merge_fields(base, base, {"status": "paused", "tags": ["a"]}).merged["status"] == "paused"
    assert merge_fields(base, {"status": "done", "tags": ["a"]}, base).merged["status"] == "done"
    conflicted = merge_fields(base, {"status": "done", "tags": ["a"]}, {"status": "paused", "tags": ["a"]})
    assert conflicted.conflicts == ["status"]
    assert conflicted.merged["status"] == "done"  # app provisionally wins; conflict is surfaced


# --- path mapping + safety ------------------------------------------------------------

def test_spec_path_table():
    assert vault_relpath("project", "nexus-prime") == "Projects/nexus-prime/README.md"
    assert vault_relpath("daily_state", "", day="2026-07-03") == "Daily/2026-07-03.md"
    assert vault_relpath("note", "crdts") == "Notes/crdts.md"
    assert vault_relpath("source", "some-paper") == "Sources/some-paper.md"
    assert vault_relpath("decision", "use-pgvector", decided_at="2026-07-03T10:00:00Z") == "Decisions/2026-07-03-use-pgvector.md"
    assert vault_relpath("person", "joao") == "People/joao.md"
    assert vault_relpath("portfolio_case", "nexus") == "Portfolio/nexus.md"
    assert vault_relpath("artifact", "diff-001", project_slug="nexus-prime") == "Artifacts/nexus-prime/diff-001.md"
    assert canvas_relpath("nexus-prime") == "Projects/nexus-prime/map.canvas"


def test_unmapped_kind_raises():
    with pytest.raises(ValueError):
        vault_relpath("sync_conflict", "x")


def test_slug_sanitization_blocks_traversal():
    assert "/" not in sanitize_slug("../../etc/passwd")
    assert ".." not in vault_relpath("note", "../escape")
    # emoji and unicode survive sanitization without breaking paths
    assert vault_relpath("note", "café-notes") == "Notes/café-notes.md"


def test_obsidian_config_is_protected():
    assert is_protected(".obsidian/app.json")
    assert is_protected("./.obsidian/workspace")
    assert is_protected(".obsidian\\windows.json")
    assert not is_protected("Notes/about-obsidian.md")


def test_sync_root_containment():
    assert is_under_sync_root("Notes/x.md")
    assert is_under_sync_root("Agent Runs/2026-07-03-abc.md")
    assert not is_under_sync_root("Random/x.md")
    assert not is_under_sync_root("Backups/vault-pre-nexus-1.tar.gz")


def test_kind_inverse_mapping():
    assert kind_for_relpath("Notes/foo.md") == "note"
    assert kind_for_relpath("Projects/x/README.md") == "project"
    assert kind_for_relpath("Random/foo.md") is None
