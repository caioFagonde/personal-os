from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_backup_precedes_update_rebuild():
    preflight = (ROOT / "scripts/preflight-update.sh").read_text()
    update = (ROOT / "scripts/update.sh").read_text()
    assert "BACKUP_ENCRYPTION_KEY" in preflight
    assert "backup before rebuild" in preflight
    assert "-d \'{\\\"include_runtime\\\":false}\'" in preflight
    assert update.index("preflight-update.sh") < update.index("docker compose")


def test_update_pipeline_has_ntfy_and_no_paid_provisioning():
    for name in ["preflight-update.sh", "update.sh"]:
        text = (ROOT / "scripts" / name).read_text()
        assert "NTFY_BASE_URL" in text and "NTFY_TOPIC" in text
    combined = "\n".join((ROOT / p).read_text() for p in ["scripts/preflight-update.sh", "scripts/update.sh", "docs/cloud-provider-strategy.md"])
    assert "az group create" not in combined
    assert "aws s3 mb" not in combined


def test_update_scripts_parse():
    for name in ["preflight-update.sh", "update.sh", "rollback-last-update.sh", "certify/backup-smoke.sh", "certify/update-smoke.sh"]:
        result = subprocess.run(["bash", "-n", str(ROOT / "scripts" / name)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_ui_exposes_azure_aws_and_encryption_setup():
    page = (ROOT / "apps/web/src/pages/BackupRestorePage.vue").read_text()
    assert "Azure Blob" in page and "AWS S3" in page and "BACKUP_ENCRYPTION_KEY" in page
    assert "/api/connectors/backup/status" in page
