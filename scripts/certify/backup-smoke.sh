#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
(cd "$ROOT/services/connector-service" && python3 -m pytest tests/test_backup.py -q)
cd "$ROOT"
python3 -m pytest tests/test_backup_update_pipeline.py -q
