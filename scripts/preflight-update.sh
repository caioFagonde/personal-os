#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONNECTOR_BACKUP_URL=${CONNECTOR_BACKUP_URL:-http://localhost:8094/api/connectors/backup/export}
BACKUP_COMMAND=${BACKUP_COMMAND:-"curl -fsS -X POST $CONNECTOR_BACKUP_URL -H 'content-type: application/json' -d '{\"include_runtime\":false}'"}
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
notify() { [[ -n "${NTFY_BASE_URL:-}" && -n "${NTFY_TOPIC:-}" ]] || return 0; $DRY_RUN && { printf '[ntfy dry-run] %s\n' "$1"; return 0; }; curl -fsS -X POST "${NTFY_BASE_URL%/}/${NTFY_TOPIC}" -H "title: Personal OS update" --data-binary "$1" >/dev/null || true; }
notify "Update preflight started"
command -v git >/dev/null
command -v docker >/dev/null
command -v curl >/dev/null
[[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]] || { echo "BACKUP_ENCRYPTION_KEY is required before update backup" >&2; notify "Update preflight blocked: backup encryption key missing"; exit 2; }
if $DRY_RUN; then
  printf '[dry-run] backup before rebuild: %s\n' "$BACKUP_COMMAND"
else
  bash -c "$BACKUP_COMMAND"
fi
notify "Update preflight backup completed"
echo "Update preflight passed"
