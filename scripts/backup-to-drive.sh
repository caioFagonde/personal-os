#!/usr/bin/env bash
# One-command data backup to Google Drive (first-usable).
#
# Chains the two existing, tested steps:
#   1. scripts/backup-v2.sh   → a complete local snapshot:
#        Postgres (pg_dump -Fc) + MinIO artifacts (mc mirror → minio.tar)
#        + optional Obsidian vault + config, sealed with a manifest.json.
#   2. scripts/backup-remote.sh <snapshot> <remote>
#        → rclone copy to the Google Drive remote, verified with rclone check,
#          recorded in remote_backup_uploads.
#
# One-time setup (no secrets ever land in the repo):
#   * MinIO artifacts:  mc alias set nexus http://127.0.0.1:${MINIO_API_PORT:-9010} "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
#                       then export MINIO_ALIAS=nexus  (put it in .env)
#   * Google Drive:     rclone config   # create a Drive remote named 'nexus-drive'
#
# Usage: scripts/backup-to-drive.sh [remote]     (remote defaults to nexus-drive)
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REMOTE="${1:-nexus-drive}"

echo "[backup-drive] 1/2 capturing snapshot (Postgres + MinIO artifacts + vault)…"
OUT="$(scripts/backup-v2.sh)"
printf '%s\n' "$OUT"
BACKUP_ID="$(printf '%s\n' "$OUT" | tail -n1)"

# backup-v2 honors BACKUP_DIR (default 'backups'); mirror that resolution here.
BACKUP_DIR_RESOLVED="${BACKUP_DIR:-backups}"
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  BACKUP_DIR_RESOLVED="$(set -a; source .env 2>/dev/null; echo "${BACKUP_DIR:-backups}")"
fi
SNAP="${BACKUP_DIR_RESOLVED}/${BACKUP_ID}"

if [[ ! -d "$SNAP" || ! -f "$SNAP/manifest.json" ]]; then
  echo "[backup-drive] no complete snapshot at '$SNAP' — aborting before upload." >&2
  exit 1
fi

echo "[backup-drive] 2/2 uploading $SNAP → $REMOTE (Google Drive)…"
scripts/backup-remote.sh "$SNAP" "$REMOTE"
echo "[backup-drive] done: ${BACKUP_ID} → ${REMOTE}"
