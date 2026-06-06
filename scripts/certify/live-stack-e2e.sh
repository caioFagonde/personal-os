#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
: "${E2E_BASE_URL:=http://127.0.0.1:9000}"
: "${COMPOSE_PROFILES:=core,apps,automation,research,ai,connectors}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for live-stack certification." >&2
  exit 2
fi
if ! command -v pnpm >/dev/null 2>&1; then
  corepack enable || true
fi

cp -n .env.example .env || true
python3 scripts/generate-env.py .env
IFS=',' read -ra profiles <<< "$COMPOSE_PROFILES"
compose_args=()
for profile in "${profiles[@]}"; do compose_args+=(--profile "$profile"); done

docker compose --env-file .env "${compose_args[@]}" up -d --build
python3 scripts/certify/wait-http.py http://127.0.0.1:8080/health 240
python3 scripts/certify/wait-http.py "$E2E_BASE_URL" 240
pnpm install --frozen-lockfile=false
pnpm exec playwright install chromium
E2E_BASE_URL="$E2E_BASE_URL" pnpm exec playwright test e2e/live-stack.spec.ts --project=chromium
