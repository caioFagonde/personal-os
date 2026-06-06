#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
(cd services/model-runtime && python3 -m pytest tests -q --cov=app.runtime --cov-branch --cov-fail-under=96)
python3 - <<'PY'
import sys
sys.path.insert(0, 'services/model-runtime')
from app.runtime import process_asset, detect_runtime_health
res = process_asset('certification-book-page.jpg', b'abc', 'image/jpeg', 'A diagram explains retrieval practice and spaced repetition.')
assert res['detections'] and res['ocr_blocks'] and res['lookup_queries']
assert detect_runtime_health()['runtimes']
print('model runtime fallback certification passed')
PY
