"""Backup manifest build/verify (Phase E4, BACKUP_RESTORE_SPEC) — pure functions.

A snapshot is a directory of component files (postgres.dump, minio.tar,
vault.tar, env-schema.json, compose.yml, migrations.txt). The manifest is the
last thing written; a snapshot with no manifest is ignored by prune/verify.

No DB, no network, no shell — unit-testable directly.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

BACKUP_FORMAT_VERSION = 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Component:
    name: str
    filename: str
    size_bytes: int
    sha256: str


@dataclass
class Manifest:
    backup_id: str
    created_at: str            # ISO 8601; passed in (scripts stamp real time)
    app_version: str
    migration_head: str
    format_version: int
    encrypted: bool
    components: list[Component] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_size_bytes"] = sum(c["size_bytes"] for c in d["components"])
        return d


def build_manifest(
    snapshot_dir: Path,
    *,
    backup_id: str,
    created_at: str,
    app_version: str,
    migration_head: str,
    encrypted: bool,
    component_files: dict[str, str],
) -> Manifest:
    """component_files maps component name → filename inside snapshot_dir."""
    components: list[Component] = []
    for name, filename in sorted(component_files.items()):
        path = snapshot_dir / filename
        if not path.exists():
            continue
        components.append(Component(name=name, filename=filename, size_bytes=path.stat().st_size, sha256=sha256_file(path)))
    return Manifest(
        backup_id=backup_id,
        created_at=created_at,
        app_version=app_version,
        migration_head=migration_head,
        format_version=BACKUP_FORMAT_VERSION,
        encrypted=encrypted,
        components=components,
    )


def write_manifest(snapshot_dir: Path, manifest: Manifest) -> Path:
    target = snapshot_dir / "manifest.json"
    target.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n")
    return target


def load_manifest(snapshot_dir: Path) -> dict[str, Any] | None:
    path = snapshot_dir / "manifest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


@dataclass
class VerifyResult:
    ok: bool
    checked: int
    failures: list[str] = field(default_factory=list)


def verify_manifest(snapshot_dir: Path, manifest: dict[str, Any]) -> VerifyResult:
    """Recompute every component's sha256 and confirm it matches the manifest."""
    failures: list[str] = []
    components = manifest.get("components", [])
    for comp in components:
        path = snapshot_dir / comp["filename"]
        if not path.exists():
            failures.append(f"missing:{comp['filename']}")
            continue
        actual = sha256_file(path)
        if actual != comp["sha256"]:
            failures.append(f"sha256_mismatch:{comp['filename']}")
    return VerifyResult(ok=not failures, checked=len(components), failures=failures)


def restore_safety_check(manifest: dict[str, Any], current_migration_head: str, migration_order: list[str]) -> tuple[bool, str]:
    """Refuse to restore a snapshot taken on an OLDER schema onto a NEWER one
    (would corrupt). Restoring same or newer-than-current is allowed."""
    head = manifest.get("migration_head", "")
    if not head or head not in migration_order:
        return False, f"unknown migration head in manifest: {head!r}"
    if current_migration_head not in migration_order:
        return False, f"unknown current migration head: {current_migration_head!r}"
    if migration_order.index(head) < migration_order.index(current_migration_head):
        return (
            False,
            f"snapshot schema {head} is older than current {current_migration_head}; "
            "restore would revert migrations — refusing. Roll the database back first.",
        )
    return True, "ok"
