#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="core"
AUTO_OPEN=false
CERTIFY_AFTER_BOOTSTRAP=false
for arg in "$@"; do
  case "$arg" in
    --full) MODE="full" ;;
    --apps) MODE="apps" ;;
    --open) AUTO_OPEN=true ;;
    --certify) CERTIFY_AFTER_BOOTSTRAP=true ;;
    --help|-h) echo "Usage: ./scripts/bootstrap.sh [--full] [--apps] [--open] [--certify]"; exit 0 ;;
  esac
done

red='\033[0;31m'; green='\033[0;32m'; yellow='\033[1;33m'; blue='\033[0;34m'; nc='\033[0m'
info(){ echo -e "${blue}→${nc} $*"; }
ok(){ echo -e "${green}✓${nc} $*"; }
warn(){ echo -e "${yellow}⚠${nc} $*"; }
fail(){ echo -e "${red}✗${nc} $*"; exit 1; }

need_cmd(){ command -v "$1" >/dev/null 2>&1 || MISSING+=("$1"); }
MISSING=()
for c in git docker; do need_cmd "$c"; done
if ! docker compose version >/dev/null 2>&1; then MISSING+=("docker compose"); fi
for c in node pnpm python3; do command -v "$c" >/dev/null 2>&1 || warn "$c not found; app/dev commands may be limited"; done
for c in adb tailscale; do command -v "$c" >/dev/null 2>&1 || warn "$c not found; optional mobile/mesh workflow skipped"; done
[[ ${#MISSING[@]} -eq 0 ]] || fail "Missing required dependencies: ${MISSING[*]}"

if [[ ! -f .env ]]; then
  info "Creating .env from .env.example with generated local-only secrets"
  cp .env.example .env
  python3 scripts/generate-env.py .env
  ok ".env generated"
else
  ok ".env already exists"
fi

info "Creating runtime folders"
mkdir -p data/{postgres,postgis,qdrant,minio,ollama,nats,ntfy,tailscale,maps,research} logs tmp cache artifacts exports generated workspace pdf-cache

grep -q '<generate' .env && fail ".env still contains placeholder values. Run: python3 scripts/generate-env.py .env"

info "Starting services ($MODE)"
case "$MODE" in
  full) docker compose --env-file .env --profile core --profile apps --profile automation --profile research --profile ai --profile connectors --profile observability up -d --build ;;
  apps) docker compose --env-file .env --profile core --profile apps --profile connectors up -d --build ;;
  core) docker compose --env-file .env --profile core up -d --build ;;
  *) fail "Unknown bootstrap mode: $MODE" ;;
esac

info "Running core migrations"
set -a; source .env; set +a
for i in {1..30}; do
  if docker compose --env-file .env exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then break; fi
  sleep 2
done
for migration in infra/postgres/migrations/*.sql; do
  info "Applying ${migration}"
  docker compose --env-file .env exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "${migration}"
done

info "Seeding module registry"
docker compose --env-file .env exec -T api-gateway python -m app.seed_modules || warn "Module seed skipped; API may still discover manifests at runtime"

info "Health checks"
curl -fsS "http://localhost:${API_GATEWAY_PORT:-8080}/health" >/dev/null && ok "API gateway healthy" || warn "API gateway not healthy yet"
curl -fsS "http://localhost:${SYNC_ENGINE_PORT:-8081}/health" >/dev/null && ok "Sync engine healthy" || warn "Sync engine not healthy yet"
curl -fsS "http://localhost:${COMMAND_BUS_PORT:-8082}/health" >/dev/null && ok "Command bus healthy" || warn "Command bus not healthy yet"
curl -fsS "http://localhost:${MODULE_SERVICE_PORT:-8083}/health" >/dev/null && ok "Module service healthy" || warn "Module service not healthy yet"
if [[ "$MODE" != "core" ]]; then
  curl -fsS "http://localhost:${CONNECTOR_SERVICE_PORT:-8094}/health" >/dev/null && ok "Connector service healthy" || warn "Connector service not healthy yet"
  curl -fsS "http://localhost:${MODEL_RUNTIME_SERVICE_PORT:-8095}/health" >/dev/null && ok "Model runtime healthy" || warn "Model runtime not healthy yet"
fi

info "Auth smoke test"
AUTH_TOKEN="$(curl -fsS -X POST "http://localhost:${API_GATEWAY_PORT:-8080}/api/devices/register" \
  -H 'content-type: application/json' \
  -d '{"device_key":"bootstrap-cli","name":"Bootstrap CLI","kind":"desktop","platform":"linux"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' 2>/dev/null || true)"
if [[ -n "${AUTH_TOKEN}" ]]; then
  curl -fsS -H "authorization: Bearer ${AUTH_TOKEN}" "http://localhost:${API_GATEWAY_PORT:-8080}/api/modules" >/dev/null && ok "Gateway auth boundary healthy" || warn "Authenticated module request failed"
else
  warn "Could not mint bootstrap auth token"
fi

TS_IP=""
if command -v tailscale >/dev/null 2>&1; then
  TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
fi

cat <<EOF

Personal OS core is starting.

Local URLs:
  API gateway:  http://localhost:${API_GATEWAY_PORT:-8080}
  Sync engine:  http://localhost:${SYNC_ENGINE_PORT:-8081}
  Command bus:  http://localhost:${COMMAND_BUS_PORT:-8082}
  Module API:   http://localhost:${MODULE_SERVICE_PORT:-8083}
  Research API: http://localhost:${RESEARCH_SERVICE_PORT:-8084}  (run: make up-research)
  Automation:   http://localhost:${AUTOMATION_SERVICE_PORT:-8085}  (run: make up-automation)
  Connectors:   http://localhost:${CONNECTOR_SERVICE_PORT:-8094}  (run: make up-connectors)
  Model runtime:http://localhost:${MODEL_RUNTIME_SERVICE_PORT:-8095}  (run: make up-model-runtime)
  MinIO:        http://localhost:9001
  NATS monitor: http://localhost:8222

Tailscale IPv4: ${TS_IP:-not detected}

Next:
  make logs
  TOKEN=$(curl -fsS -X POST http://localhost:${API_GATEWAY_PORT:-8080}/api/devices/register -H 'content-type: application/json' -d '{"device_key":"cli","name":"CLI","kind":"desktop","platform":"linux"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
  curl -H "authorization: Bearer $TOKEN" http://localhost:${API_GATEWAY_PORT:-8080}/api/modules
  curl -H "authorization: Bearer $TOKEN" http://localhost:${API_GATEWAY_PORT:-8080}/api/proxy/sync/api/sync/health

Open onboarding:
  http://localhost:${WEB_PORT:-9000}/onboarding
EOF

if [[ "${BOOTSTRAP_AUTOMATION_INTERACTIVE:-true}" == "true" ]]; then
  info "Running interactive authorization handoff for Tailscale, ADB, and OAuth when configured"
  ./scripts/onboarding/auto-authorize.sh || warn "Interactive authorization handoff incomplete; continue from /onboarding"
fi

if [[ "${MOBILE_AUTO_DEPLOY:-false}" == "true" ]]; then
  if command -v adb >/dev/null 2>&1 && adb devices | awk 'NR>1 && $2=="device" {found=1} END{exit !found}'; then
    info "Deploying Android app to authorized USB device"
    make mobile || warn "Mobile deploy failed; use apps/mobile preflight output"
  else
    warn "MOBILE_AUTO_DEPLOY requested but no authorized ADB device is available"
  fi
fi


if [[ "$CERTIFY_AFTER_BOOTSTRAP" == "true" ]]; then
  info "Running Phase 13 local certification"
  ./scripts/certify/full-local.sh || warn "Base certification reported failures; inspect output and /certification"
  ./scripts/certify/model-runtime.sh || warn "Model runtime certification failed; inspect /model-runtime"
  ./scripts/certify/release-readiness.py || warn "Initial version readiness gate failed; inspect /initial-readiness"
fi

if [[ "$AUTO_OPEN" == "true" ]]; then
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:${WEB_PORT:-9000}/onboarding" >/dev/null 2>&1 || true; fi
fi
