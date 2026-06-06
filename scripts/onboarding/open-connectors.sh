#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://localhost:9000}"
URL="$BASE/connectors"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; else echo "$URL"; fi
