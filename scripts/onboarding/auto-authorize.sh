#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
set -a; [[ -f .env ]] && source .env; set +a
WAIT_SECONDS="${BOOTSTRAP_WAIT_FOR_AUTH_SECONDS:-600}"
open_url(){ if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1 || true; else echo "Open: $1"; fi; }
wait_for(){ local name="$1" cmd="$2"; local deadline=$((SECONDS+WAIT_SECONDS)); until eval "$cmd" >/dev/null 2>&1; do if (( SECONDS > deadline )); then echo "Timed out waiting for $name"; return 1; fi; sleep 3; done; echo "✓ $name ready"; }

wait_for_connector_account(){
  local provider="$1"
  local url="http://localhost:${CONNECTOR_SERVICE_PORT:-8094}/api/connectors"
  local deadline=$((SECONDS+WAIT_SECONDS))
  until curl -fsS "$url" 2>/dev/null | python3 -c 'import json,sys; provider=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(a.get("provider")==provider and a.get("status")=="active" for a in data.get("cloud_accounts", [])) else 1)' "$provider" >/dev/null 2>&1
  do
    if (( SECONDS > deadline )); then echo "Timed out waiting for ${provider} OAuth callback"; return 1; fi
    sleep 3
  done
  echo "✓ ${provider} OAuth connected"
}

if command -v tailscale >/dev/null 2>&1; then
  if ! tailscale status >/dev/null 2>&1; then
    echo "Tailscale is installed but not authorized. Opening Tailscale login..."
    tailscale up --accept-routes=false || true
    wait_for "Tailscale authorization" "tailscale ip -4"
  else
    echo "✓ Tailscale already authorized"
  fi
else
  echo "Tailscale CLI not found. Install Tailscale or use the Docker sidecar with TAILSCALE_AUTHKEY."
fi

if command -v adb >/dev/null 2>&1; then
  echo "Checking USB Android device authorization..."
  adb start-server >/dev/null 2>&1 || true
  if ! adb devices | awk 'NR>1 && $2=="device" {found=1} END{exit !found}'; then
    echo "Connect phone by USB, enable USB debugging, and accept the RSA prompt. Waiting..."
    wait_for "ADB authorized device" "adb devices | awk 'NR>1 && \$2==\"device\" {found=1} END{exit !found}'"
  else
    echo "✓ ADB authorized device detected"
  fi
else
  echo "ADB not found; skipping mobile USB automation."
fi

if [[ -n "${GOOGLE_CLIENT_ID:-}" && -n "${GOOGLE_CLIENT_SECRET:-}" ]]; then
  open_url "${CONNECTOR_PUBLIC_BASE_URL:-http://localhost:8080}/api/proxy/connectors/api/connectors/google/open"
  if [[ "${BOOTSTRAP_WAIT_FOR_OAUTH:-true}" == "true" ]]; then wait_for_connector_account google || true; fi
fi
if [[ -n "${MICROSOFT_CLIENT_ID:-}" && -n "${MICROSOFT_CLIENT_SECRET:-}" ]]; then
  open_url "${CONNECTOR_PUBLIC_BASE_URL:-http://localhost:8080}/api/proxy/connectors/api/connectors/microsoft/open"
  if [[ "${BOOTSTRAP_WAIT_FOR_OAUTH:-true}" == "true" ]]; then wait_for_connector_account microsoft || true; fi
fi
open_url "http://localhost:${WEB_PORT:-9000}/connectors"
