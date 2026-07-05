#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
find artifacts/release -type f -name '*.sha256' -print0 | while IFS= read -r -d '' f; do
  (cd "$(dirname "$f")" && sha256sum -c "$(basename "$f")")
done
