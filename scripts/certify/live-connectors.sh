#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export RUN_LIVE_CONNECTOR_TESTS="${RUN_LIVE_CONNECTOR_TESTS:-true}"
python3 -m pytest tests/live -q -m live
