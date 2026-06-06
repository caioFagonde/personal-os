#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

run(){ echo "\n==> $*"; "$@"; }

run python3 -m pytest tests -q
run ./scripts/check-secrets.sh
run python3 -m compileall -q services scripts

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  [[ -f .env ]] || { cp .env.example .env; python3 scripts/generate-env.py .env; }
  run docker compose --env-file .env --profile core config
  run docker compose --env-file .env --profile connectors config
  run docker compose --env-file .env --profile full config
else
  echo "Docker unavailable; skipping compose validation."
fi

if command -v pnpm >/dev/null 2>&1; then
  run pnpm install --frozen-lockfile=false
  run pnpm --dir apps/web test
  run pnpm --dir apps/mobile validate
  run pnpm --dir apps/desktop validate
else
  echo "pnpm unavailable; skipping frontend/native shell validation."
fi

if command -v cargo >/dev/null 2>&1; then
  run cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml --lib
else
  echo "cargo unavailable; skipping Tauri Rust tests."
fi
