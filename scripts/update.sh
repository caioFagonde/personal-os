#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
notify() { [[ -n "${NTFY_BASE_URL:-}" && -n "${NTFY_TOPIC:-}" ]] || return 0; $DRY_RUN && { printf '[ntfy dry-run] %s\n' "$1"; return 0; }; curl -fsS -X POST "${NTFY_BASE_URL%/}/${NTFY_TOPIC}" -H "title: Personal OS update" --data-binary "$1" >/dev/null || true; }
run() { if $DRY_RUN; then printf '[dry-run] %s\n' "$*"; else "$@"; fi; }
if $DRY_RUN; then "$ROOT/scripts/preflight-update.sh" --dry-run; else "$ROOT/scripts/preflight-update.sh"; fi
BEFORE_REF=$(git rev-parse HEAD)
notify "Update rebuild started"
run docker compose --env-file .env --profile full build
run docker compose --env-file .env --profile full up -d
AFTER_REF=$(git rev-parse HEAD)
if ! $DRY_RUN; then mkdir -p tmp/update; printf '%s\n%s\n' "$BEFORE_REF" "$AFTER_REF" > tmp/update/last-update.refs; fi
notify "Update completed"
echo "Update completed; rollback metadata recorded locally"
