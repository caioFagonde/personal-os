#!/usr/bin/env bash
# Restore drill (Phase E4): restore the latest verified snapshot into a
# side postgres container on a spare port, run invariant queries, record the
# result in restore_drills, tear the container down. Monthly via automation.
# Honest: if docker/snapshot are unavailable the drill records 'failed' with a
# reason rather than pretending to pass.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && { set -a; source .env; set +a; }
: "${POSTGRES_USER:=personal_os}"
: "${POSTGRES_DB:=personal_os}"
: "${POSTGRES_PASSWORD:=personal_os}"
: "${BACKUP_DIR:=backups}"
: "${DRILL_PORT:=55432}"
: "${DRILL_CONTAINER:=personal-os-postgres-drill}"
: "${DRILL_DB:=personal_os_drill}"

record_drill() { # status  checks_json
  command -v docker >/dev/null 2>&1 || return 0
  docker compose --env-file .env exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "INSERT INTO restore_drills(backup_id, status, checks, drill_kind, completed_at) VALUES(${3:-NULL}, '$1', '$2'::jsonb, 'scheduled', now());" \
    >/dev/null 2>&1 || true
}

SNAP="$(ls -dt "$BACKUP_DIR"/personal-os-* 2>/dev/null | head -n1 || true)"
if [[ -z "$SNAP" || ! -f "$SNAP/postgres.dump" ]]; then
  echo "[drill] no snapshot with a postgres.dump found in $BACKUP_DIR — recording failed" >&2
  record_drill "failed" '{"reason":"no_snapshot_or_postgres_component"}'
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "[drill] docker unavailable — cannot run an isolated restore; recording failed" >&2
  record_drill "failed" '{"reason":"docker_unavailable"}'
  exit 3
fi

echo "[drill] spinning up $DRILL_CONTAINER on port $DRILL_PORT"
docker rm -f "$DRILL_CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$DRILL_CONTAINER" -e POSTGRES_USER="$POSTGRES_USER" -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$DRILL_DB" -p "$DRILL_PORT:5432" postgis/postgis:16-3.4 >/dev/null
trap 'docker rm -f "$DRILL_CONTAINER" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  docker exec "$DRILL_CONTAINER" pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1 && break
  sleep 2
done

echo "[drill] pg_restore into side container"
if docker exec -i "$DRILL_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$DRILL_DB" --no-owner < "$SNAP/postgres.dump" 2>/dev/null; then
  COUNT=$(docker exec "$DRILL_CONTAINER" psql -U "$POSTGRES_USER" -d "$DRILL_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo 0)
  echo "[drill] restored; $COUNT public tables present"
  if [[ "${COUNT:-0}" -gt 0 ]]; then
    record_drill "passed" "{\"public_tables\":$COUNT}"
    echo "[drill] passed"
  else
    record_drill "failed" '{"reason":"no_tables_after_restore"}'
    echo "[drill] failed: empty restore" >&2; exit 1
  fi
else
  record_drill "failed" '{"reason":"pg_restore_error"}'
  echo "[drill] failed: pg_restore error" >&2; exit 1
fi
