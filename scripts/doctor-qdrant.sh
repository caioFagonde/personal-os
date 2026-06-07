#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${QDRANT_URL:-http://localhost:${QDRANT_PORT:-6333}}"
MAX_WAIT_SECONDS="${QDRANT_DOCTOR_WAIT_SECONDS:-60}"
DEADLINE=$((SECONDS + MAX_WAIT_SECONDS))

echo "→ Checking Qdrant at ${BASE_URL}"
while (( SECONDS < DEADLINE )); do
  if curl -fsS "${BASE_URL}/healthz" >/dev/null 2>&1; then
    echo "✓ Qdrant healthz is ready"
    exit 0
  fi
  if curl -fsS "${BASE_URL}/" >/dev/null 2>&1; then
    echo "✓ Qdrant HTTP API is reachable"
    exit 0
  fi
  sleep 2
done

echo "✗ Qdrant did not become reachable at ${BASE_URL}" >&2
echo "  Diagnostics:" >&2
docker compose ps qdrant >&2 || true
docker compose logs --tail=120 qdrant >&2 || true
exit 1
