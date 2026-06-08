#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "${1:-}" == "--execute" ]] || { echo "Dry-run only. Pass --execute after reviewing the recorded revision."; [[ -f tmp/update/last-update.refs ]] && sed -n '1p' tmp/update/last-update.refs; exit 0; }
[[ -f tmp/update/last-update.refs ]] || { echo "No rollback metadata found" >&2; exit 2; }
TARGET=$(sed -n '1p' tmp/update/last-update.refs)
[[ -n "$TARGET" ]] || exit 2
./scripts/preflight-update.sh
[[ -z "$(git status --porcelain)" ]] || { echo "Working tree must be clean before rollback" >&2; exit 2; }
git switch --detach "$TARGET"
docker compose --env-file .env --profile full up -d --build
echo "Rollback completed at $TARGET"
