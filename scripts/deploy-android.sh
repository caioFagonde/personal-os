#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/mobile"
command -v pnpm >/dev/null 2>&1 || { echo "pnpm missing"; exit 1; }
command -v adb >/dev/null 2>&1 || { echo "adb missing"; exit 1; }
pnpm install
pnpm validate
pnpm cap:add:android
pnpm cap:sync
pnpm android:run
