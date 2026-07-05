"""Phase E4 unit tests — backup manifest build/verify + prune policy math.

Pure-logic tests (no Postgres, rclone, age, or MinIO). The orchestration
scripts are syntax-checked in test_phase_e_continuity.py.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backup.manifest import build_manifest, load_manifest, restore_safety_check, verify_manifest, write_manifest  # noqa: E402
from backup.prune import Snapshot, plan_prune, select_keep  # noqa: E402


def _make_snapshot(tmp_path: Path) -> Path:
    snap = tmp_path / "personal-os-20260703-000000"
    snap.mkdir()
    (snap / "postgres.dump").write_bytes(b"PGDMP custom format bytes")
    (snap / "vault.tar").write_bytes(b"vault archive bytes")
    (snap / "env-schema.json").write_text('{"keys": ["POSTGRES_DB"]}')
    return snap


def test_manifest_round_trip_and_totals(tmp_path):
    snap = _make_snapshot(tmp_path)
    manifest = build_manifest(
        snap, backup_id="bk1", created_at="2026-07-03T00:00:00Z", app_version="0.7.0",
        migration_head="017_backup_v2.sql", encrypted=False,
        component_files={"postgres": "postgres.dump", "vault": "vault.tar", "config": "env-schema.json", "absent": "nope.bin"},
    )
    write_manifest(snap, manifest)
    loaded = load_manifest(snap)
    assert loaded["backup_id"] == "bk1"
    assert loaded["format_version"] == 2
    assert len(loaded["components"]) == 3  # the absent file is skipped
    assert loaded["total_size_bytes"] == sum(c["size_bytes"] for c in loaded["components"])


def test_verify_detects_corruption(tmp_path):
    snap = _make_snapshot(tmp_path)
    manifest = build_manifest(
        snap, backup_id="bk1", created_at="2026-07-03T00:00:00Z", app_version="0.7.0",
        migration_head="017_backup_v2.sql", encrypted=False,
        component_files={"postgres": "postgres.dump", "vault": "vault.tar"},
    )
    write_manifest(snap, manifest)
    loaded = load_manifest(snap)
    assert verify_manifest(snap, loaded).ok
    (snap / "vault.tar").write_bytes(b"tampered bytes!!")
    result = verify_manifest(snap, loaded)
    assert not result.ok
    assert "sha256_mismatch:vault.tar" in result.failures


def test_verify_flags_missing_component(tmp_path):
    snap = _make_snapshot(tmp_path)
    manifest = build_manifest(
        snap, backup_id="bk1", created_at="2026-07-03T00:00:00Z", app_version="0.7.0",
        migration_head="017_backup_v2.sql", encrypted=False,
        component_files={"postgres": "postgres.dump"},
    )
    write_manifest(snap, manifest)
    loaded = load_manifest(snap)
    (snap / "postgres.dump").unlink()
    result = verify_manifest(snap, loaded)
    assert not result.ok and "missing:postgres.dump" in result.failures


def test_no_manifest_returns_none(tmp_path):
    empty = tmp_path / "incomplete"
    empty.mkdir()
    assert load_manifest(empty) is None  # incomplete snapshot ignored by verify/prune


def test_restore_refuses_older_schema_onto_newer():
    order = ["001_core.sql", "016_vault_sync.sql", "017_backup_v2.sql"]
    ok, _ = restore_safety_check({"migration_head": "017_backup_v2.sql"}, "016_vault_sync.sql", order)
    assert ok  # newer/equal snapshot is fine
    ok2, msg = restore_safety_check({"migration_head": "001_core.sql"}, "017_backup_v2.sql", order)
    assert not ok2 and "older" in msg


def test_prune_keeps_daily_weekly_monthly():
    base = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)
    # 40 daily snapshots
    snaps = [Snapshot(f"d{i}", base - timedelta(days=i), verified=False) for i in range(40)]
    keep = select_keep(snaps, keep_daily=7, keep_weekly=4, keep_monthly=6)
    # 7 daily + up to 4 distinct weeks + up to 2 distinct months over 40 days
    assert len(keep) >= 7
    assert "d0" in keep  # newest always kept


def test_prune_never_deletes_only_verified_copy():
    base = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)
    # newest 7 are unverified; the only verified one is 30 days old (out of daily window)
    snaps = [Snapshot(f"d{i}", base - timedelta(days=i), verified=(i == 30)) for i in range(35)]
    keep, delete = plan_prune(snaps, keep_daily=7, keep_weekly=0, keep_monthly=0)
    assert "d30" in keep, "the only verified copy must survive prune"
    assert "d30" not in delete


def test_prune_marks_extras_for_deletion():
    base = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)
    snaps = [Snapshot(f"d{i}", base - timedelta(days=i), verified=False) for i in range(20)]
    keep, delete = plan_prune(snaps, keep_daily=7, keep_weekly=0, keep_monthly=0)
    assert len(delete) > 0
    assert set(keep).isdisjoint(set(delete))
