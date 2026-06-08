#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
python3 -m pytest tests/test_backup_update_pipeline.py -q
bash -n scripts/preflight-update.sh scripts/update.sh scripts/rollback-last-update.sh
