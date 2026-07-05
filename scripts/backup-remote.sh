#!/usr/bin/env bash
# Push a verified snapshot to a remote (Phase E4). Uses rclone; the remote is
# configured interactively via `rclone config` (no secrets in the repo). Copies,
# verifies with `rclone check`, then records remote_backup_uploads.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SNAP="${1:-}"
REMOTE="${2:-nexus-drive}"   # rclone remote name (nexus-drive | nexus-disk)
: "${RCLONE_DEST_DIR:=NexusBackups}"
[[ -n "$SNAP" && -d "$SNAP" ]] || { echo "Usage: scripts/backup-remote.sh backups/<snapshot-dir> [remote]" >&2; exit 2; }
[[ -f "$SNAP/manifest.json" ]] || { echo "No manifest.json — refusing to upload an incomplete snapshot." >&2; exit 2; }

if ! command -v rclone >/dev/null 2>&1; then
  cat >&2 <<MSG
rclone not installed. Install it and configure a remote interactively:
  rclone config          # create '$REMOTE' (Google Drive) — OAuth stays local
  cp scripts/rclone/rclone.conf.template ~/.config/rclone/rclone.conf  # as a starting point
Then re-run: scripts/backup-remote.sh "$SNAP" "$REMOTE"
MSG
  exit 3
fi

BASE="$(basename "$SNAP")"
echo "[remote] rclone copy $SNAP → $REMOTE:$RCLONE_DEST_DIR/$BASE"
rclone copy "$SNAP" "$REMOTE:$RCLONE_DEST_DIR/$BASE" --checksum
echo "[remote] rclone check"
rclone check "$SNAP" "$REMOTE:$RCLONE_DEST_DIR/$BASE" --one-way

BACKUP_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backup_id"])' "$SNAP/manifest.json")"
PROVIDER="rclone_drive"; [[ "$REMOTE" == "nexus-disk" ]] && PROVIDER="rclone_disk"
if command -v docker >/dev/null 2>&1 && [[ -f .env ]]; then
  set -a; source .env; set +a
  docker compose --env-file .env exec -T postgres psql -U "${POSTGRES_USER:-personal_os}" -d "${POSTGRES_DB:-personal_os}" -c \
    "INSERT INTO remote_backup_uploads(backup_id, provider, remote_uri, status, completed_at) VALUES('${BACKUP_ID}','${PROVIDER}','${REMOTE}:${RCLONE_DEST_DIR}/${BASE}','uploaded',now());" \
    >/dev/null 2>&1 && echo "[remote] recorded upload for ${BACKUP_ID}" || echo "[remote] upload done; could not record row (DB down?)"
fi
echo "[remote] uploaded ${BACKUP_ID} to ${REMOTE}"
