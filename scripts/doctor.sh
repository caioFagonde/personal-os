#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
check(){ if command -v "$1" >/dev/null 2>&1; then echo "✓ $1: $($1 --version 2>/dev/null | head -1)"; else echo "✗ $1 missing"; fi }
check git
check docker
docker compose version || true
check node
check pnpm
check python3
check adb
check tailscale
[[ -f .env ]] && echo "✓ .env present" || echo "✗ .env missing"
./scripts/check-secrets.sh || true
if [[ -f .env ]]; then
  docker compose --env-file .env ps || true
fi
