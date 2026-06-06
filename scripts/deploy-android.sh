#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/web"
command -v adb >/dev/null 2>&1 || { echo "adb missing"; exit 1; }
pnpm install
pnpm build
pnpm cap:sync
pnpm cap:run:android
