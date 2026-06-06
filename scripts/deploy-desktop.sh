#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/desktop"
pnpm install
pnpm tauri dev
