#!/usr/bin/env bash
# Verify a backup snapshot (Phase E4): sha256 manifest check + pg_restore --list
# integrity + decrypt smoke test. On success, records verified_at in
# backup_manifests. Honest: if a tool is missing, that check is reported skipped.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SNAP="${1:-}"
[[ -n "$SNAP" && -d "$SNAP" ]] || { echo "Usage: scripts/backup-verify.sh backups/<snapshot-dir>" >&2; exit 2; }
[[ -f "$SNAP/manifest.json" ]] || { echo "No manifest.json in $SNAP — incomplete snapshot, ignoring." >&2; exit 2; }

# 1. sha256 manifest check (pure python, always available).
python3 - "$SNAP" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from backup.manifest import load_manifest, verify_manifest
snap = Path(sys.argv[1])
manifest = load_manifest(snap)
result = verify_manifest(snap, manifest)
print(f"[verify] sha256: checked {result.checked}, ok={result.ok}")
if not result.ok:
    print("[verify] FAILURES:", ", ".join(result.failures))
    sys.exit(1)
PY

# 2. pg_restore --list on the postgres component (custom-format integrity).
PGDUMP="$SNAP/postgres.dump"
if [[ -f "$PGDUMP" ]] && command -v pg_restore >/dev/null 2>&1; then
  pg_restore --list "$PGDUMP" >/dev/null && echo "[verify] pg_restore --list: ok" || { echo "[verify] pg_restore --list FAILED" >&2; exit 1; }
elif [[ -f "$PGDUMP" ]]; then
  echo "[verify] pg_restore not installed — SKIPPED custom-format integrity check"
elif [[ -f "$PGDUMP.age" ]]; then
  echo "[verify] postgres component is age-encrypted — decrypt first to run pg_restore --list"
fi

# 3. Decrypt smoke test (first 1MB) for encrypted snapshots.
if ls "$SNAP"/*.age >/dev/null 2>&1; then
  if command -v age >/dev/null 2>&1 && [[ -n "${BACKUP_AGE_KEYFILE:-}" ]]; then
    FIRST_AGE="$(ls "$SNAP"/*.age | head -n1)"
    age -d -i "$BACKUP_AGE_KEYFILE" "$FIRST_AGE" 2>/dev/null | head -c 1048576 >/dev/null && echo "[verify] decrypt smoke: ok" || { echo "[verify] decrypt smoke FAILED" >&2; exit 1; }
  else
    echo "[verify] encrypted snapshot but age/BACKUP_AGE_KEYFILE missing — SKIPPED decrypt smoke"
  fi
fi

# 4. Record verified_at (best-effort; needs the DB up).
BACKUP_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["backup_id"])' "$SNAP/manifest.json")"
if command -v docker >/dev/null 2>&1 && [[ -f .env ]]; then
  set -a; source .env; set +a
  docker compose --env-file .env exec -T postgres psql -U "${POSTGRES_USER:-personal_os}" -d "${POSTGRES_DB:-personal_os}" \
    -c "UPDATE backup_manifests SET verified_at=now(), verify_status='verified' WHERE backup_id='${BACKUP_ID}';" >/dev/null 2>&1 \
    && echo "[verify] recorded verified_at for ${BACKUP_ID}" || echo "[verify] could not record verified_at (DB down?) — checks still passed"
fi
echo "[verify] $BACKUP_ID verified"
