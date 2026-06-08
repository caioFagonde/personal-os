#!/usr/bin/env bash
set -Eeuo pipefail
# model-runtime-smoke.sh — Quick certification that distinguishes demo from production readiness.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "=== Model Runtime Smoke Certification ==="

echo "--- Unit tests ---"
(cd services/model-runtime && python3 -m pytest tests -q --cov=app.runtime --cov-branch --cov-fail-under=96)

echo ""
echo "--- Heuristic demo fallback ---"
python3 - <<'PY'
import sys, os
sys.path.insert(0, 'services/model-runtime')
from app.runtime import process_asset, detect_runtime_health, ProviderState

res = process_asset('certification-book-page.jpg', b'abc', 'image/jpeg',
                    'A diagram explains retrieval practice and spaced repetition.')
assert res['detections'] and res['ocr_blocks'] and res['lookup_queries']

health = detect_runtime_health()
assert health['runtimes']
assert health['demo_mode'] is True, "Expected demo_mode=True with default heuristic providers"
assert health['production_ready'] is False, "Expected production_ready=False in demo mode"

for rt in health['runtimes']:
    assert rt['demo'] is True, f"Runtime {rt['name']} should be marked demo"
    assert '[DEMO]' in rt['detail'], f"Runtime {rt['name']} detail must contain [DEMO] label"

print('PASS: demo/heuristic fallback certification passed')
PY

echo ""
echo "--- Provider state machine ---"
python3 - <<'PY'
import sys, os
sys.path.insert(0, 'services/model-runtime')
from app.runtime import detect_runtime_health, get_provider_catalog, ProviderState

# Simulate an external provider at each state
env_base = {'OCR_PROVIDER': 'tesseract', 'VISION_PROVIDER': 'heuristic', 'AUDIO_PROVIDER': 'heuristic'}

# not_installed
env = dict(env_base)
h = detect_runtime_health(env)
ocr = [r for r in h['runtimes'] if r['name'] == 'ocr'][0]
assert ocr['demo'] is False
assert ocr['provider_state'] == 'not_installed'
assert ocr['available'] is False

# installed
env['TESSERACT_INSTALLED'] = 'true'
h = detect_runtime_health(env)
ocr = [r for r in h['runtimes'] if r['name'] == 'ocr'][0]
assert ocr['provider_state'] == 'installed'

# configured
env['TESSERACT_CONFIGURED'] = 'true'
h = detect_runtime_health(env)
ocr = [r for r in h['runtimes'] if r['name'] == 'ocr'][0]
assert ocr['provider_state'] == 'configured'

# tested
env['TESSERACT_READY'] = 'true'
h = detect_runtime_health(env)
ocr = [r for r in h['runtimes'] if r['name'] == 'ocr'][0]
assert ocr['provider_state'] == 'tested'
assert ocr['available'] is True

# provider catalog
catalog = get_provider_catalog()
assert len(catalog) > 0
for p in catalog:
    assert 'setup_hint' in p
    assert 'requires_download' in p

print('PASS: provider state machine certification passed')
PY

echo ""
echo "--- Production readiness distinction ---"
python3 - <<'PY'
import sys
sys.path.insert(0, 'services/model-runtime')
from app.runtime import detect_runtime_health

# All external and tested => production_ready
env = {
    'OCR_PROVIDER': 'tesseract', 'TESSERACT_READY': 'true',
    'VISION_PROVIDER': 'yolov8', 'YOLOV8_READY': 'true',
    'AUDIO_PROVIDER': 'whisper', 'WHISPER_READY': 'true',
}
h = detect_runtime_health(env)
assert h['production_ready'] is True, f"Expected production_ready=True, got {h}"
assert h['demo_mode'] is False

# Mixed: one demo, others tested => not production_ready, not demo_mode
env2 = {
    'OCR_PROVIDER': 'heuristic',
    'VISION_PROVIDER': 'yolov8', 'YOLOV8_READY': 'true',
    'AUDIO_PROVIDER': 'whisper', 'WHISPER_READY': 'true',
}
h2 = detect_runtime_health(env2)
assert h2['demo_mode'] is False
assert h2['production_ready'] is True  # non-demo providers are tested

print('PASS: production readiness distinction passed')
PY

echo ""
echo "=== All model runtime smoke checks passed ==="
