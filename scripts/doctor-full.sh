#!/usr/bin/env bash
# Full health check: Docker Compose config, ports, service endpoints, auth, connectors, model runtime.
# Usage: ./scripts/doctor-full.sh [--profile core|apps|full]
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE="${1:-core}"
case "$PROFILE" in --profile) PROFILE="${2:-core}" ;; esac

red='\033[0;31m'; green='\033[0;32m'; yellow='\033[1;33m'; blue='\033[0;34m'; nc='\033[0m'
PASS=0; FAIL=0; WARN=0

ok()   { echo -e "${green}✓${nc} $*";  ((PASS++)); }
fail() { echo -e "${red}✗${nc} $*";    ((FAIL++)); }
warn() { echo -e "${yellow}⚠${nc} $*"; ((WARN++)); }
info() { echo -e "${blue}→${nc} $*"; }

info "Validating configuration (values are never printed)..."
if python3 scripts/validate-env.py .env; then
  ok "Configuration values are well formed"
else
  fail "Configuration has errors — fix the named variables and rerun doctor"
fi

# ---------------------------------------------------------------------------
# 1. Compose config
# ---------------------------------------------------------------------------
info "Checking Docker Compose config..."
if docker compose --env-file .env --profile full config >/dev/null 2>&1; then
  ok "docker-compose.yml parses cleanly under --profile full"
else
  fail "docker-compose.yml has config errors"
  docker compose --env-file .env --profile full config 2>&1 | tail -20 | sed 's/^/  /' || true
fi

# ---------------------------------------------------------------------------
# 2. .env present and generated
# ---------------------------------------------------------------------------
if [[ -f .env ]]; then
  ok ".env present"
  if grep -q '<generate' .env 2>/dev/null; then
    fail ".env still contains placeholder values — run: python3 scripts/generate-env.py .env"
  else
    ok ".env has no placeholder values"
  fi
else
  fail ".env not found — run: cp .env.example .env && python3 scripts/generate-env.py .env"
fi

# ---------------------------------------------------------------------------
# 3. Docker running
# ---------------------------------------------------------------------------
if docker info >/dev/null 2>&1; then
  ok "Docker daemon is running"
else
  fail "Docker daemon is not running — start Docker and retry"
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. Service health endpoints (load port values from .env if available)
# ---------------------------------------------------------------------------
set -a; [[ -f .env ]] && source .env 2>/dev/null || true; set +a

API_PORT="${API_GATEWAY_PORT:-8080}"
SYNC_PORT="${SYNC_ENGINE_PORT:-8081}"
CMD_PORT="${COMMAND_BUS_PORT:-8082}"
MOD_PORT="${MODULE_SERVICE_PORT:-8083}"
CONN_PORT="${CONNECTOR_SERVICE_PORT:-8094}"
MODEL_PORT="${MODEL_RUNTIME_SERVICE_PORT:-8095}"
AGENT_PORT="${CODING_AGENT_SERVICE_PORT:-8096}"
WEB_PORT_VAL="${WEB_PORT:-9000}"
MINIO_PORT="${MINIO_CONSOLE_PORT:-9001}"
NATS_PORT="8222"

check_http() {
  local label="$1" url="$2" optional="${3:-false}"
  if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
    ok "$label ($url)"
  else
    if [[ "$optional" == "true" ]]; then
      warn "$label not reachable — optional service ($url)"
    else
      fail "$label not reachable ($url)"
      echo "    Recovery: make up && make migrate"
    fi
  fi
}

info "Checking core service health endpoints..."
check_http "API gateway"    "http://localhost:${API_PORT}/health"
check_http "Sync engine"    "http://localhost:${SYNC_PORT}/health"
check_http "Command bus"    "http://localhost:${CMD_PORT}/health"
check_http "Module service" "http://localhost:${MOD_PORT}/health"

if [[ "$PROFILE" != "core" ]]; then
  info "Checking optional service health endpoints..."
  check_http "Connector service" "http://localhost:${CONN_PORT}/health"  true
  check_http "Model runtime"     "http://localhost:${MODEL_PORT}/health"  true
  check_http "Coding agent"      "http://localhost:${AGENT_PORT}/health"  true
  check_http "Web UI"            "http://localhost:${WEB_PORT_VAL}"       true
  check_http "MinIO console"     "http://localhost:${MINIO_PORT}"         true
  check_http "NATS monitor"      "http://localhost:${NATS_PORT}/healthz"  true
fi

# ---------------------------------------------------------------------------
# 5. Port conflicts (check no other process is fighting on core ports)
# ---------------------------------------------------------------------------
info "Checking for port conflicts..."
for port in "$API_PORT" "$SYNC_PORT" "$CMD_PORT" "$MOD_PORT"; do
  if ss -tlnH "sport = :${port}" 2>/dev/null | grep -q LISTEN; then
    ok "Port ${port} is listening"
  else
    warn "Port ${port} not listening — is the service up?"
  fi
done

# ---------------------------------------------------------------------------
# 6. Auth smoke test
# ---------------------------------------------------------------------------
info "Running auth smoke test..."
AUTH_PAYLOAD='{"device_key":"doctor-cli","name":"Doctor CLI","kind":"desktop","platform":"linux"}'
AUTH_RESP="$(curl -fsS --max-time 5 -X POST "http://localhost:${API_PORT}/api/devices/register" \
  -H 'content-type: application/json' -d "${AUTH_PAYLOAD}" 2>/dev/null || echo '')"
TOKEN="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("access_token",""))' \
  <<<"${AUTH_RESP}" 2>/dev/null || echo '')"

if [[ -n "$TOKEN" ]]; then
  ok "Device registration returned access_token"
  if curl -fsS --max-time 5 -H "authorization: Bearer ${TOKEN}" \
       "http://localhost:${API_PORT}/api/modules" >/dev/null 2>&1; then
    ok "Authenticated /api/modules request succeeded"
  else
    fail "Authenticated /api/modules request failed"
    echo "    Recovery: make migrate && make seed"
  fi
else
  fail "Device registration failed (gateway may be down or not yet migrated)"
  echo "    Recovery: make up && make migrate && make seed"
fi

# ---------------------------------------------------------------------------
# 7. Connector service status (optional)
# ---------------------------------------------------------------------------
if curl -fsS --max-time 3 "http://localhost:${CONN_PORT}/health" >/dev/null 2>&1; then
  info "Checking connector service providers..."
  CONN_STATUS="$(curl -fsS --max-time 5 "http://localhost:${CONN_PORT}/api/connectors/status" 2>/dev/null || echo '{}')"
  for provider in google microsoft twilio ntfy tailscale; do
    configured="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('${provider}',{}).get('configured','false'))" \
      <<<"${CONN_STATUS}" 2>/dev/null || echo false)"
    if [[ "$configured" == "True" || "$configured" == "true" ]]; then
      ok "Connector: ${provider} configured"
    else
      warn "Connector: ${provider} not configured — set env vars and restart connector-service"
    fi
  done
fi

# ---------------------------------------------------------------------------
# 8. Restart-loop detection
# ---------------------------------------------------------------------------
info "Checking for restart loops..."
RESTARTING="$(docker compose --env-file .env ps 2>/dev/null | grep -i "restart" | awk '{print $1}' | head -10 || true)"
if [[ -n "$RESTARTING" ]]; then
  fail "Services in restart loop: ${RESTARTING}"
  echo "    Recovery: docker compose --env-file .env logs ${RESTARTING}"
else
  ok "No services in restart loop"
fi

# ---------------------------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo -e " Doctor report: ${green}${PASS} passed${nc} · ${yellow}${WARN} warnings${nc} · ${red}${FAIL} failed${nc}"
echo "================================================================"
echo ""
echo "Service URLs:"
echo "  Web UI:        http://localhost:${WEB_PORT_VAL}"
echo "  API gateway:   http://localhost:${API_PORT}"
echo "  Sync engine:   http://localhost:${SYNC_PORT}"
echo "  Command bus:   http://localhost:${CMD_PORT}"
echo "  MinIO:         http://localhost:${MINIO_PORT}"
echo "  NATS monitor:  http://localhost:${NATS_PORT}"
if [[ "$PROFILE" != "core" ]]; then
echo "  Connectors:    http://localhost:${CONN_PORT}"
echo "  Model runtime: http://localhost:${MODEL_PORT}"
echo "  Coding agent:  http://localhost:${AGENT_PORT}"
fi
echo ""
if [[ "$FAIL" -gt 0 ]]; then
  echo "  Run 'make up && make migrate' to recover from most failures."
  exit 1
fi
