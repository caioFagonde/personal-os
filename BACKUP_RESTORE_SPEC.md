# BACKUP_RESTORE_SPEC.md — Continuity & Disaster Recovery

## Current state (verified)

- `scripts/backup.sh`: pg_dump + tar of `data artifacts exports generated`. Local only, unencrypted, no manifest verification.
- `scripts/restore.sh`, `scripts/restore-drill.sh`, `scripts/certify/backup-smoke.sh`, `update.sh`/`rollback-last-update.sh` exist.
- Tables: `backup_manifests`, `remote_backup_uploads`, `restore_drills` — schema exists, remote path unwired.
- No rclone anywhere; no encryption; no scheduling; MinIO objects not included in backup.sh.

## Target: 3-2-1 for a single-owner system

Local snapshot (disk) → second copy (external disk or NAS via rclone local remote) → offsite (Google Drive via rclone, encrypted). All orchestrated by one script family, all recorded in `backup_manifests`, all verifiable.

## Backup contents (one snapshot = one manifest)

| Component | Method |
|---|---|
| Postgres | `pg_dump -Fc` (custom format → parallel restore, integrity-checkable with `pg_restore --list`) |
| MinIO buckets | `mc mirror` (or rclone S3 remote) → `minio/` in snapshot |
| Obsidian vault roots | tar of configured roots (respecting user opt-in) |
| Config | `.env` **excluded**; instead `generated/env-schema.json` (keys only, no values) + compose file + migration list |
| Manifest | `manifest.json`: snapshot id, created_at, component list, sizes, sha256 per file, app version, migration head |

## Encryption

`age` (simple, scriptable, no GPG keyring pain):
- `scripts/backup-keygen.sh` → age keypair; **private key stored outside the repo/data dirs**, printed once with instructions to store in a password manager; public key in `.env` as `BACKUP_AGE_RECIPIENT`.
- Snapshot tarball piped through `age -r $BACKUP_AGE_RECIPIENT` before any remote upload. Local copy optionally encrypted too (`BACKUP_ENCRYPT_LOCAL=true`).
- Restore requires the private key; `restore-drill` verifies decryption quarterly.

## rclone template (new: `scripts/rclone/`)

- `rclone.conf.template` with two remotes: `nexus-drive` (Google Drive, OAuth done via `rclone config` interactively — no secrets in repo) and `nexus-disk` (local/USB path).
- `scripts/backup-remote.sh`: `rclone copy backups/<snapshot>.tar.gz.age nexus-drive:NexusBackups/ --checksum`, then `rclone check`, then insert into `remote_backup_uploads` with status + checksum.
- Retention: `scripts/backup-prune.sh` — keep 7 daily, 4 weekly, 6 monthly (local and remote via `rclone delete --min-age` guarded by manifest cross-check; never deletes the only verified copy).

## Verification & drills

- `scripts/backup-verify.sh <snapshot>`: sha256 manifest check + `pg_restore --list` + decrypt test (first 1MB) → writes `verified_at` on the manifest row.
- **Restore drill** (monthly, automated via automation-service recipe): spin `postgres-drill` container on a side port, restore latest snapshot, run invariant queries (row counts per core table within tolerance of manifest metadata, migration head matches), record in `restore_drills`, tear down. Attention chip if a drill is >35 days old or failed.
- Update pipeline: `preflight-update.sh` must require a verified backup < 24h old before `update.sh` proceeds (add the check).

## Artifact packaging & release continuity

- Release archives built with `git archive` only (fixes shipped `node_modules/dist` hygiene failure R-20); hygiene test moves to CI.
- `scripts/release/build-manifest.py` (exists) extended to include backup-format version so restores across versions are diagnosable.

## Surfaces

`/continuity` Backup tab: last snapshot age, verified?, remote copy age, drill status, retention summary, and three buttons: Back up now, Verify latest, Run drill — each calling an allowlisted ops runner endpoint (command-bus template, approval-gated), never raw shell from the UI.

## Failure modes handled explicitly

- Drive quota/exhausted → upload row `failed` + Attention chip; local copies unaffected.
- Key lost → documented recovery stance: unencrypted local copies (if enabled) or none; the keygen script prints this warning at creation time.
- Partial snapshot (service down mid-dump) → manifest written last; no manifest = snapshot ignored by prune/verify.
- Restore onto newer schema → restore script compares migration head, refuses with instructions instead of corrupting.

## Tests

- Unit: manifest build/verify, prune policy math, retention never-delete-last-verified rule.
- Integration (compose lane): full backup → corrupt one byte → verify fails; backup → restore into drill container → invariants pass.
- Contract: preflight-update blocks without fresh verified backup; UI buttons hit approval-gated endpoints only.
