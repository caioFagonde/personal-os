#!/usr/bin/env bash
set -euo pipefail
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p backups
set -a; source .env; set +a
docker compose --env-file .env exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "backups/postgres-$STAMP.sql"
tar -czf "backups/runtime-$STAMP.tar.gz" data artifacts exports generated 2>/dev/null || true
echo "Backup written to backups/postgres-$STAMP.sql and backups/runtime-$STAMP.tar.gz"
