-- Phase E4: backup v2 manifest metadata + broader remote providers.
-- Extends backup_manifests (009) with the richer manifest fields from
-- BACKUP_RESTORE_SPEC; widens remote_backup_uploads providers to include
-- the rclone remotes. All idempotent.

ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS format_version INT NOT NULL DEFAULT 1;
ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS app_version TEXT;
ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS migration_head TEXT;
ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS components JSONB NOT NULL DEFAULT '[]';
ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS total_size_bytes BIGINT NOT NULL DEFAULT 0;
ALTER TABLE backup_manifests ADD COLUMN IF NOT EXISTS verify_status TEXT NOT NULL DEFAULT 'unverified';

-- restore drill freshness: attention chip fires when the newest passed drill is stale.
ALTER TABLE restore_drills ADD COLUMN IF NOT EXISTS drill_kind TEXT NOT NULL DEFAULT 'scheduled';

-- Widen the remote upload provider set to include the rclone remotes
-- (nexus-drive = offsite Google Drive, nexus-disk = second local/USB copy).
ALTER TABLE remote_backup_uploads DROP CONSTRAINT IF EXISTS remote_backup_uploads_provider_check;
ALTER TABLE remote_backup_uploads
  ADD CONSTRAINT remote_backup_uploads_provider_check
  CHECK (provider IN ('google','microsoft','rclone_drive','rclone_disk','minio'));

-- Approval-gated ops-runner templates for the Continuity backup buttons.
-- The UI never runs raw shell; it creates a command_request against one of
-- these allowlisted local_script templates, which the trusted host runner
-- executes after approval.
INSERT INTO command_templates(id, name, description, command_kind, allowed_scopes, requires_approval, local_only, template)
VALUES
  ('backup.create', 'Back up now', 'Create a v2 backup snapshot (pg_dump -Fc + MinIO + vault + manifest).', 'local_script', ARRAY['backup.write'], true, true, '{"executor":"host-runner","script":"scripts/backup-v2.sh"}'),
  ('backup.verify', 'Verify latest backup', 'Verify the newest snapshot (sha256 + pg_restore --list + decrypt smoke).', 'local_script', ARRAY['backup.write'], true, true, '{"executor":"host-runner","script":"scripts/backup-verify.sh"}'),
  ('backup.drill', 'Run restore drill', 'Restore the latest snapshot into a side container and check invariants.', 'local_script', ARRAY['backup.write'], true, true, '{"executor":"host-runner","script":"scripts/backup-drill.sh"}')
ON CONFLICT (id) DO NOTHING;
