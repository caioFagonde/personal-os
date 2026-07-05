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

# Phase E4 gate: require a VERIFIED backup < 24h old before an update proceeds.
# Opt-out for environments without the DB reachable at preflight time.
REQUIRE_VERIFIED_BACKUP=${REQUIRE_VERIFIED_BACKUP:-true}
MANIFESTS_URL=${CONNECTOR_MANIFESTS_URL:-http://localhost:8094/api/connectors/backup/manifests}
if [[ "$REQUIRE_VERIFIED_BACKUP" == "true" ]] && ! $DRY_RUN; then
  if command -v curl >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    if curl -fsS "$MANIFESTS_URL" 2>/dev/null | python3 -c '
import json, sys
from datetime import datetime, timezone
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(3)
now = datetime.now(timezone.utc)
for r in rows:
    v = r.get("verified_at")
    if not v:
        continue
    try:
        ts = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        continue
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if (now - ts).total_seconds() < 24 * 3600:
        sys.exit(0)
sys.exit(1)
'; then
      echo "Verified backup < 24h confirmed"
    else
      echo "No verified backup < 24h old. Run: make backup && scripts/backup-verify.sh backups/<snapshot>" >&2
      notify "Update preflight blocked: no verified backup < 24h"
      echo "Set REQUIRE_VERIFIED_BACKUP=false to override (not recommended)." >&2
      exit 2
    fi
  else
    echo "curl/python3 unavailable — cannot confirm verified backup freshness; set REQUIRE_VERIFIED_BACKUP=false to proceed anyway." >&2
    exit 2
  fi
fi
echo "Update preflight passed"
