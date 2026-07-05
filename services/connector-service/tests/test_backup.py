import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.backup import BackupConfigurationError, backup_setup_status, create_backup_bundle, validate_restore_manifest


def test_create_backup_bundle_is_encrypted_and_excludes_env(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".env").write_text("SECRET=bad\n")
    (root / ".env.example").write_text("SECRET=\n")
    key = Fernet.generate_key().decode()
    manifest = create_backup_bundle(root, tmp_path / "out", include=[".env", ".env.example"], encryption_key=key)
    assert manifest.encrypted and manifest.archive_path.endswith(".tar.gz.enc")
    assert ".env" not in manifest.included_paths and ".env.example" in manifest.included_paths
    assert not Path(manifest.archive_path).read_bytes().startswith(b"\x1f\x8b")
    stored = json.loads((tmp_path / "out" / f"{manifest.backup_id}.json").read_text())
    assert validate_restore_manifest(stored)


def test_backup_requires_valid_encryption_key(tmp_path: Path):
    with pytest.raises(BackupConfigurationError):
        create_backup_bundle(tmp_path, tmp_path / "out", encryption_key="")
    with pytest.raises(BackupConfigurationError):
        create_backup_bundle(tmp_path, tmp_path / "out", encryption_key="invalid")


def test_cloud_setup_states_require_least_privilege_configuration():
    status = backup_setup_status({})
    assert status["encryption"]["status"] == "needs_encryption_key"
    assert status["providers"]["azure_blob"]["status"] == "needs_configuration"
    assert status["providers"]["aws_s3"]["status"] == "needs_configuration"
    assert status["automatic_paid_provisioning"] is False
    ready = backup_setup_status({"BACKUP_ENCRYPTION_KEY":"set", "AZURE_BACKUP_ACCOUNT":"a", "AZURE_BACKUP_CONTAINER":"c", "AZURE_BACKUP_CONTAINER_SAS":"s", "AWS_BACKUP_BUCKET":"b", "AWS_BACKUP_ROLE_ARN":"r"})
    assert ready["providers"]["azure_blob"]["configured"]
    assert ready["providers"]["aws_s3"]["configured"]
    assert "root" in ready["providers"]["aws_s3"]["credential_policy"]
