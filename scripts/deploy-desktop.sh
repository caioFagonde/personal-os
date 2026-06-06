#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/desktop"
command -v pnpm >/dev/null 2>&1 || { echo "pnpm missing"; exit 1; }
pnpm install
pnpm validate
pnpm dev
