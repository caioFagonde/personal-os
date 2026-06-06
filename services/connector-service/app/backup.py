from __future__ import annotations

import hashlib
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path
from time import time


@dataclass(frozen=True)
class BackupManifest:
    backup_id: str
    archive_path: str
    sha256: str
    created_at: float
    included_paths: tuple[str, ...]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup_bundle(root: Path, out_dir: Path, include: list[str] | None = None) -> BackupManifest:
    include = include or [".env.example", "modules", "docs", "scripts", "infra/postgres/migrations"]
    out_dir.mkdir(parents=True, exist_ok=True)
    backup_id = f"personal-os-backup-{int(time())}"
    archive = out_dir / f"{backup_id}.tar.gz"
    safe_paths: list[str] = []
    with tarfile.open(archive, "w:gz") as tar:
        for rel in include:
            path = root / rel
            if not path.exists():
                continue
            if path.name == ".env" or path.name.endswith(".local") or path.name.endswith(".secret"):
                continue
            tar.add(path, arcname=rel)
            safe_paths.append(rel)
    manifest = BackupManifest(backup_id, str(archive), sha256_file(archive), time(), tuple(safe_paths))
    (out_dir / f"{backup_id}.json").write_text(json.dumps(manifest.__dict__, indent=2, sort_keys=True) + "\n")
    return manifest


def validate_restore_manifest(manifest: dict) -> bool:
    required = {"backup_id", "archive_path", "sha256", "created_at", "included_paths"}
    return required.issubset(manifest) and isinstance(manifest.get("included_paths"), (list, tuple))
