from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import time

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class BackupManifest:
    backup_id: str
    archive_path: str
    sha256: str
    created_at: float
    included_paths: tuple[str, ...]
    encrypted: bool = True
    encryption_key_version: str = "backup-v1"


class BackupConfigurationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_setup_status(env: dict[str, str]) -> dict:
    encryption_ready = bool(env.get("BACKUP_ENCRYPTION_KEY"))
    azure_ready = bool(env.get("AZURE_BACKUP_ACCOUNT") and env.get("AZURE_BACKUP_CONTAINER") and env.get("AZURE_BACKUP_CONTAINER_SAS"))
    aws_ready = bool(env.get("AWS_BACKUP_BUCKET") and (env.get("AWS_BACKUP_ROLE_ARN") or env.get("AWS_PROFILE")))
    return {
        "encryption": {
            "status": "ready" if encryption_ready else "needs_encryption_key",
            "configured": encryption_ready,
            "required_env": ["BACKUP_ENCRYPTION_KEY"],
            "message": "Encrypted backup export is ready." if encryption_ready else "Set BACKUP_ENCRYPTION_KEY to a Fernet key before creating backups.",
        },
        "providers": {
            "azure_blob": {
                "id": "azure_blob", "status": "ready" if azure_ready else "needs_configuration", "configured": azure_ready,
                "required_env": ["AZURE_BACKUP_ACCOUNT", "AZURE_BACKUP_CONTAINER", "AZURE_BACKUP_CONTAINER_SAS"],
                "credential_policy": "Use a container-scoped SAS with write/create/list only; do not use an account key.",
                "automatic_provisioning": False,
            },
            "aws_s3": {
                "id": "aws_s3", "status": "ready" if aws_ready else "needs_configuration", "configured": aws_ready,
                "required_env": ["AWS_BACKUP_BUCKET", "AWS_BACKUP_ROLE_ARN or AWS_PROFILE"],
                "credential_policy": "Use a bucket-scoped role/profile with object write/list only; do not use root credentials.",
                "automatic_provisioning": False,
            },
        },
        "automatic_paid_provisioning": False,
    }


def create_backup_bundle(root: Path, out_dir: Path, include: list[str] | None = None, *, encryption_key: str | None = None, encryption_key_version: str | None = None) -> BackupManifest:
    include = include or [".env.example", "modules", "docs", "scripts", "infra/postgres/migrations"]
    encryption_key = encryption_key or os.environ.get("BACKUP_ENCRYPTION_KEY")
    if not encryption_key:
        raise BackupConfigurationError("BACKUP_ENCRYPTION_KEY is required; plaintext backup export is disabled")
    try:
        cipher = Fernet(encryption_key.encode())
    except (TypeError, ValueError) as exc:
        raise BackupConfigurationError("BACKUP_ENCRYPTION_KEY must be a valid Fernet key") from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    backup_id = f"personal-os-backup-{int(time())}"
    archive = out_dir / f"{backup_id}.tar.gz.enc"
    safe_paths: list[str] = []
    with tempfile.TemporaryDirectory(prefix="personal-os-backup-") as temp_dir:
        plaintext_archive = Path(temp_dir) / f"{backup_id}.tar.gz"
        with tarfile.open(plaintext_archive, "w:gz") as tar:
            for rel in include:
                path = root / rel
                if not path.exists():
                    continue
                if path.name == ".env" or path.name.endswith(".local") or path.name.endswith(".secret"):
                    continue
                tar.add(path, arcname=rel)
                safe_paths.append(rel)
        archive.write_bytes(cipher.encrypt(plaintext_archive.read_bytes()))
    manifest = BackupManifest(backup_id, str(archive), sha256_file(archive), time(), tuple(safe_paths), encryption_key_version=encryption_key_version or os.environ.get("BACKUP_ENCRYPTION_KEY_VERSION", "backup-v1"))
    (out_dir / f"{backup_id}.json").write_text(json.dumps(manifest.__dict__, indent=2, sort_keys=True) + "\n")
    return manifest


def validate_restore_manifest(manifest: dict) -> bool:
    required = {"backup_id", "archive_path", "sha256", "created_at", "included_paths", "encrypted", "encryption_key_version"}
    return required.issubset(manifest) and manifest.get("encrypted") is True and isinstance(manifest.get("included_paths"), (list, tuple))
