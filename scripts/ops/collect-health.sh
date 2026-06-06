#!/usr/bin/env bash
set -euo pipefail
API_URL="${API_URL:-http://localhost:8080}"
for path in /health /metrics /api/release; do
  echo "--- ${API_URL}${path}"
  curl -fsS "${API_URL}${path}" | head -80
  echo
 done
