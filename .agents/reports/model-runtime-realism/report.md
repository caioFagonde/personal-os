# Report: model-runtime-realism

## Summary

Distinguished demo heuristic fallbacks from real OCR/object/audio providers by adding:
- A `ProviderState` enum (not_installed → installed → configured → tested)
- `demo` and `provider_state` fields on every runtime health entry
- Top-level `demo_mode` and `production_ready` flags in the health response
- A provider catalog endpoint (`GET /api/model-runtime/providers`) listing known providers with setup hints and download warnings
- UI banners clearly showing demo vs production status, with per-runtime state badges
- `scripts/setup-models.sh` — interactive provider installer that never downloads without explicit consent
- `scripts/certify/model-runtime-smoke.sh` — certification that explicitly validates demo labeling and provider state transitions
- Makefile targets: `certify-model-runtime-smoke`, `setup-models`

## Files changed

| File | Change |
|------|--------|
| `services/model-runtime/app/runtime.py` | Added ProviderState enum, ProviderInfo dataclass, demo/provider_state fields on RuntimeHealth, KNOWN_PROVIDERS catalog, get_provider_catalog(), _is_demo(), _provider_state() helpers; updated _available() to accept env dict; updated _detail() to include [DEMO] prefix |
| `services/model-runtime/app/main.py` | Added `/api/model-runtime/providers` endpoint |
| `services/model-runtime/tests/test_runtime.py` | Added 6 new tests: demo labeling, provider state machine, production_ready flag, mixed mode, provider catalog, catalog env reflection |
| `apps/web/src/pages/ModelRuntimePage.vue` | Added demo/production banners, per-runtime state badges, provider catalog list with download warnings |
| `scripts/setup-models.sh` | New — interactive provider setup with explicit consent gates |
| `scripts/certify/model-runtime-smoke.sh` | New — smoke certification that validates demo vs production distinction |
| `Makefile` | Added `certify-model-runtime-smoke` and `setup-models` targets |

## Tests run and results

- `python3 -m pytest services/model-runtime/tests -q` → **13 passed** (0.03s)
- `python3 -m pytest tests/test_phase13_scaffold.py::test_model_runtime_service_is_wired -q` → **1 passed**
- `bash -n scripts/setup-models.sh` → OK
- `bash -n scripts/certify/model-runtime-smoke.sh` → OK
- Inline smoke assertions (demo labeling, state machine, production readiness, catalog) → all pass

## Acceptance status

| Criterion | Status |
|-----------|--------|
| Heuristic mode is labeled demo-only | PASS — `[DEMO]` in detail, `demo: true` in response, UI banner |
| Real providers have installed/configured/tested states | PASS — ProviderState enum, env-driven progression |
| No automatic large downloads without explicit consent | PASS — setup-models.sh requires interactive confirmation; UI shows "large download" badge |
| UI and certification distinguish demo from production readiness | PASS — banners, badges, smoke script validates both paths |

## Remaining risks

- No actual integration with real providers (tesseract, whisper, etc.) — only the state machine and declarations exist. Actual inference adapters are out of scope for this task.
- Coverage flags (`--cov`) not available in the test environment (pytest-cov not installed); Makefile target referencing them will need pytest-cov in CI.

## Suggested follow-up tasks

- Implement real inference adapters (tesseract OCR, whisper transcription, YOLOv8 detection) behind the declared provider interface.
- Add a `POST /api/model-runtime/providers/{name}/test` endpoint that runs a validation sample and transitions state to "tested".
- Install pytest-cov in the model-runtime requirements-dev or CI image.
