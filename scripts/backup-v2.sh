#!/usr/bin/env bash
# Backup v2 (Phase E4, BACKUP_RESTORE_SPEC): one snapshot = one manifest.
#   Postgres  → pg_dump -Fc (custom format, pg_restore --list verifiable)
#   MinIO     → mc mirror / rclone into minio/
#   Vault     → tar of configured Obsidian roots (opt-in)
#   Config    → generated/env-schema.json (keys only) + compose + migration list
#   Manifest  → manifest.json, written LAST (no manifest ⇒ snapshot ignored)
# Optional age encryption of the packed snapshot before any remote upload.
# Degrades honestly: missing tools are reported, never silently skipped.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && { set -a; source .env; set +a; }
: "${POSTGRES_USER:=personal_os}"
: "${POSTGRES_DB:=personal_os}"
: "${BACKUP_DIR:=backups}"
: "${BACKUP_ENCRYPT:=false}"          # age-encrypt the packed snapshot
: "${BACKUP_INCLUDE_VAULT:=false}"    # honor Obsidian vault opt-in
: "${OBSIDIAN_VAULT_PATH:=}"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ID="personal-os-${STAMP}"
SNAP="${BACKUP_DIR}/${BACKUP_ID}"
mkdir -p "$SNAP"
COMPOSE="docker compose --env-file .env"

log() { printf '[backup-v2] %s\n' "$*"; }

# 1. Postgres (custom format for parallel/verifiable restore).
if command -v docker >/dev/null 2>&1; then
  log "pg_dump -Fc → postgres.dump"
  if ! $COMPOSE exec -T postgres pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" > "$SNAP/postgres.dump" 2>/dev/null; then
    rm -f "$SNAP/postgres.dump"
    log "pg_dump failed (stack down?) — SKIPPING postgres component (honest partial snapshot)"
  fi
else
  log "docker not available — SKIPPING postgres.dump (honest partial snapshot)"
fi

# 2. MinIO buckets.
if command -v mc >/dev/null 2>&1 && [[ -n "${MINIO_ALIAS:-}" ]]; then
  log "mc mirror → minio.tar"
  mc mirror --quiet "${MINIO_ALIAS}/${MINIO_BUCKET:-artifacts}" "$SNAP/minio/" || log "mc mirror failed (continuing)"
  tar -czf "$SNAP/minio.tar" -C "$SNAP" minio 2>/dev/null && rm -rf "$SNAP/minio" || true
else
  log "mc not configured — SKIPPING minio (set MINIO_ALIAS to include object storage)"
fi

# 3. Obsidian vault (opt-in only).
if [[ "$BACKUP_INCLUDE_VAULT" == "true" && -n "$OBSIDIAN_VAULT_PATH" && -d "$OBSIDIAN_VAULT_PATH" ]]; then
  log "tar vault roots → vault.tar"
  tar -czf "$SNAP/vault.tar" -C "$OBSIDIAN_VAULT_PATH" . 2>/dev/null || log "vault tar failed (continuing)"
fi

# 4. Config: env schema (KEYS ONLY, never values), compose, migration list.
if [[ -f .env.example ]]; then
  grep -oE '^[A-Z0-9_]+=' .env.example | sed 's/=$//' | python3 -c 'import sys,json; print(json.dumps({"keys":[l.strip() for l in sys.stdin if l.strip()]}, indent=2))' > "$SNAP/env-schema.json"
fi
cp docker-compose.yml "$SNAP/compose.yml" 2>/dev/null || true
ls infra/postgres/migrations/*.sql 2>/dev/null | xargs -n1 basename > "$SNAP/migrations.txt" || true
MIGRATION_HEAD="$(tail -n1 "$SNAP/migrations.txt" 2>/dev/null || echo unknown)"
APP_VERSION="$(git -C "$ROOT" describe --tags --always 2>/dev/null || echo dev)"

# 5. Optional age encryption of each component.
ENCRYPTED=false
if [[ "$BACKUP_ENCRYPT" == "true" ]]; then
  if command -v age >/dev/null 2>&1 && [[ -n "${BACKUP_AGE_RECIPIENT:-}" ]]; then
    for f in "$SNAP"/*; do
      [[ "$(basename "$f")" == "manifest.json" ]] && continue
      age -r "$BACKUP_AGE_RECIPIENT" -o "$f.age" "$f" && rm -f "$f"
    done
    ENCRYPTED=true
    log "age-encrypted snapshot components"
  else
    log "BACKUP_ENCRYPT=true but age/BACKUP_AGE_RECIPIENT missing — writing PLAINTEXT (run scripts/backup-keygen.sh)"
  fi
fi

# 6. Manifest LAST (its presence marks the snapshot complete).
python3 - "$SNAP" "$BACKUP_ID" "$APP_VERSION" "$MIGRATION_HEAD" "$ENCRYPTED" <<'PY'
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, "scripts")  # cwd is repo ROOT (set by the script)
from backup.manifest import build_manifest, write_manifest
snap, backup_id, app_version, head, encrypted = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] == "True"
files = {}
for p in sorted(snap.iterdir()):
    if p.name == "manifest.json":
        continue
    files[p.stem] = p.name
m = build_manifest(snap, backup_id=backup_id, created_at=datetime.now(timezone.utc).isoformat(),
                   app_version=app_version, migration_head=head, encrypted=encrypted, component_files=files)
write_manifest(snap, m)
print(f"[backup-v2] manifest: {len(m.components)} components, head {head}")
PY

log "snapshot ready: $SNAP (id $BACKUP_ID)"
echo "$BACKUP_ID"
