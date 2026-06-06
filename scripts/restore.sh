#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 backups/postgres-YYYYmmdd-HHMMSS.sql"; exit 1; }
set -a; source .env; set +a
read -rp "This will restore into $POSTGRES_DB. Type RESTORE to continue: " confirm
[[ "$confirm" == "RESTORE" ]] || exit 1
docker compose --env-file .env exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$1"
