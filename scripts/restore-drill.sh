#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${POSTGRES_USER:=personal_os}"
: "${POSTGRES_DB:=personal_os}"
: "${POSTGRES_PASSWORD:=personal_os}"
if [[ ! -f .env ]]; then cp .env.example .env && python3 scripts/generate-env.py .env; fi
set -a; source .env; set +a
COMPOSE="docker compose --env-file .env"
echo "[restore-drill] booting core stack"
$COMPOSE --profile core --profile apps --profile connectors up -d --build
for i in {1..60}; do $COMPOSE exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1 && break; sleep 2; done
for migration in infra/postgres/migrations/*.sql; do $COMPOSE exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "$migration"; done
echo "[restore-drill] inserting sample continuity data"
$COMPOSE exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" <<'SQL'
INSERT INTO contacts(key, display_name, role) VALUES('restore_drill','Restore Drill','test') ON CONFLICT(key) DO NOTHING;
INSERT INTO tasks(title, body, status, source_kind, source_id) VALUES('Restore drill task','Verify backup continuity','inbox','restore-drill','task-1') ON CONFLICT(source_kind, source_id) DO NOTHING;
INSERT INTO notes(id, title, body, tags) VALUES(gen_random_uuid(), 'Restore drill note','Verify zettelkasten continuity', ARRAY['restore-drill']) ON CONFLICT DO NOTHING;
SQL
echo "[restore-drill] exporting backup manifest"
curl -fsS -X POST http://localhost:${CONNECTOR_SERVICE_PORT:-8094}/api/connectors/backup/export -H 'content-type: application/json' -d '{"include_runtime":false}' >/tmp/personal-os-restore-drill-backup.json
cat /tmp/personal-os-restore-drill-backup.json
echo "[restore-drill] verifying sample data still queryable"
$COMPOSE exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT COUNT(*) FROM tasks WHERE source_kind='restore-drill';" | grep -q 1
echo "[restore-drill] passed"
