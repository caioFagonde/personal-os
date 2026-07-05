#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

OUT_DIR="artifacts/release/desktop"
mkdir -p "$OUT_DIR"
command -v pnpm >/dev/null 2>&1 || { echo "pnpm is required" >&2; exit 2; }
command -v cargo >/dev/null 2>&1 || { echo "cargo is required" >&2; exit 2; }

pnpm install --frozen-lockfile=false
pnpm --dir apps/web build
if [[ -n "${TAURI_SIGNING_PRIVATE_KEY:-}" ]]; then
  echo "Tauri signing key detected; tauri build will sign/update metadata when configured."
else
  echo "TAURI_SIGNING_PRIVATE_KEY not set; building unsigned desktop bundle."
fi
pnpm --dir apps/desktop build
if [[ -d apps/desktop/src-tauri/target/release/bundle ]]; then
  tar -czf "$OUT_DIR/personal-os-tauri-bundle.tar.gz" -C apps/desktop/src-tauri/target/release bundle
  sha256sum "$OUT_DIR/personal-os-tauri-bundle.tar.gz" > "$OUT_DIR/personal-os-tauri-bundle.tar.gz.sha256"
fi
