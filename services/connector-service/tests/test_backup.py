import json
from pathlib import Path

from app.backup import create_backup_bundle, validate_restore_manifest


def test_create_backup_bundle_excludes_env(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".env").write_text("SECRET=bad\n")
    (root / ".env.example").write_text("SECRET=\n")
    (root / "docs").mkdir()
    (root / "docs" / "a.md").write_text("ok\n")
    manifest = create_backup_bundle(root, tmp_path / "backups", include=[".env", ".env.example", "docs"])
    assert ".env" not in manifest.included_paths
    assert ".env.example" in manifest.included_paths
    assert Path(manifest.archive_path).exists()
    stored = json.loads((tmp_path / "backups" / f"{manifest.backup_id}.json").read_text())
    assert validate_restore_manifest(stored)
