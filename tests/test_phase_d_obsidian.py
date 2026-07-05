"""Phase D contract tests — Obsidian vault integration.

Locks in: the pure schema/merge/path modules, migration 016, the vault-sync
endpoints and their safety rules (dry-run default, write gated by setting,
pre-enable backup, deletes never propagated, .obsidian protected), the legacy
export/import contracts, and the web UX wiring.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONNECTOR = ROOT / "services/connector-service/app"
WEB = ROOT / "apps/web/src"


def read(path: Path) -> str:
    return path.read_text()


# --- D1/D2: pure modules behave (importable everywhere: no asyncpg in them) --------

def test_pure_modules_do_not_import_db_drivers():
    for module in ("vault_schema.py", "vault_paths.py", "vault_merge.py"):
        text = read(CONNECTOR / module)
        assert "asyncpg" not in text, f"{module} must stay pure (goldens run without DB deps)"
        assert "import httpx" not in text


def test_frontmatter_uses_safe_yaml_only():
    text = read(CONNECTOR / "vault_schema.py")
    assert "yaml.safe_load" in text
    assert "yaml.load(" not in text
    assert "FRONTMATTER_MAX_BYTES" in text


def test_task_line_is_obsidian_tasks_compatible():
    from services.connector_service.app.vault_schema import parse_task_lines, render_task_line
    line = render_task_line({"id": "018f3c00-0000-4000-8000-000000000001", "title": "T", "status": "inbox", "due_at": "2026-07-10", "priority": 2})
    assert "📅 2026-07-10" in line and "[nexus:: task/" in line
    assert parse_task_lines(line)[0]["id"] == "018f3c00-0000-4000-8000-000000000001"


def test_merge_matrix_via_import():
    from services.connector_service.app.vault_merge import merge_bodies
    base = "a\nb\nc\n"
    assert not merge_bodies(base, "a\nX\nc\n", base).conflict
    assert not merge_bodies(base, base, "a\nY\nc\n").conflict
    assert merge_bodies(base, "a\nX\nc\n", "a\nY\nc\n").conflict


def test_migration_016_idempotent_vault_files():
    sql = read(ROOT / "infra/postgres/migrations/016_vault_sync.sql")
    assert "CREATE TABLE IF NOT EXISTS vault_files" in sql
    assert "base_snapshot" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql


# --- D3: sync engine safety rules ------------------------------------------------------

def test_sync_endpoints_exist():
    main = read(CONNECTOR / "main.py")
    for route in (
        '"/api/connectors/obsidian/sync/status"',
        '"/api/connectors/obsidian/sync/files"',
        '"/api/connectors/obsidian/sync/index"',
        '"/api/connectors/obsidian/sync/run"',
        '"/api/connectors/obsidian/sync/enable"',
        '"/api/connectors/obsidian/sync/resolve"',
        '"/api/connectors/obsidian/projects/{project_id}/canvas"',
    ):
        assert route in main, f"missing vault-sync route {route}"


def test_legacy_export_import_contracts_survive():
    main = read(CONNECTOR / "main.py")
    assert 'with target.open("x", encoding="utf-8")' in main       # export stays create-only
    assert 'dry_run_only_detail("obsidian", "import")' in main      # legacy import stays dry-run


def test_write_is_gated_by_setting_and_dry_run_is_default():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "obsidian_vault_write" in sync
    assert "await self.write_enabled()" in sync
    main = read(CONNECTOR / "main.py")
    assert "execute: bool = False" in main  # dry-run default on sync requests


def test_enable_runs_pre_enable_vault_backup():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "vault-pre-nexus-" in sync
    assert "tarfile" in sync
    assert "backup_vault_roots" in sync


def test_deletes_are_never_propagated():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "deletes are never propagated" in sync.lower()
    assert "DELETE FROM notes" not in sync
    assert "DELETE FROM projects" not in sync
    assert ".unlink(" not in sync  # never removes vault files


def test_obsidian_config_dir_protected_and_writes_contained():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "is_protected" in sync
    assert "resolve_contained" in sync
    assert "self.vault not in target.parents" in sync
    assert ".nexus-tmp" in sync and ".replace(" in sync  # atomic temp+rename writes


def test_vault_notes_without_nexus_id_become_captures():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "obsidian_note" in sync
    assert "capture_items" in sync


def test_task_checkbox_round_trip_completes_tasks():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "_apply_task_checkboxes" in sync
    assert "status='completed'" in sync


def test_wikilinks_become_reference_edges_on_inbound():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "extract_wikilinks" in sync
    assert "'references'" in sync


def test_conflicts_live_in_vault_files_with_resolutions():
    sync = read(CONNECTOR / "vault_sync.py")
    assert "keep_app" in sync and "keep_vault" in sync
    assert "status='conflict'" in sync


# --- D4: web UX -------------------------------------------------------------------------

def test_settings_has_vault_section_with_confirmed_enable():
    text = read(WEB / "pages/SettingsPage.vue")
    assert "vault-settings" in text
    assert "sync/enable" in text
    assert "Backups/vault-pre-nexus" in text          # the dialog explains the backup
    assert "confirmEnable" in text                     # enable requires confirmation
    assert "path/validate" in text


def test_notes_show_sync_chips():
    text = read(WEB / "pages/ZettelkastenPage.vue")
    assert "syncChips" in text
    assert "sync/files" in text
    for state in ("synced", "pending", "conflict"):
        assert state in text


def test_continuity_has_vault_tab_with_resolution():
    text = read(WEB / "pages/ContinuityPage.vue")
    assert '"vault"' in text or "'vault'" in text
    assert "sync/resolve" in text
    assert "keep_app" in text and "keep_vault" in text
    assert "last_run" in text  # indexer lag surfaced


# --- dependency + docs --------------------------------------------------------------------

def test_pyyaml_pinned_for_connector():
    requirements = read(ROOT / "services/connector-service/requirements.txt")
    assert "PyYAML" in requirements


def test_docs_updated_for_phase_d():
    plan = read(ROOT / "docs/IMPLEMENTATION_PLAN.md")
    assert "Phase D" in plan
    handoff = read(ROOT / "NEW_AGENT_HANDOFF.md")
    assert "vault" in handoff.lower()
