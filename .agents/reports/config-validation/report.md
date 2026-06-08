# Config Validation Report

## 1. Root cause / diagnosis

- No `scripts/validate-env.py` existed, so malformed values reached Compose and
  runtime services.
- Bootstrap and doctor only checked for placeholders; they did not validate
  URLs, ports, phone numbers, OAuth redirects, or cloud config shapes.
- API gateway settings accepted arbitrary values, returned secret-like setting
  values, and wrote raw setting values into audit metadata.
- The requested settings page and reusable config form did not exist.

## 2. Files changed

- `scripts/validate-env.py`
- `scripts/doctor-full.sh`
- `services/api-gateway/app/config_validation.py`
- `services/api-gateway/app/main.py`
- `apps/web/src/components/NexusConfigForm.vue`
- `apps/web/src/pages/SettingsPage.vue`
- `tests/test_config_validation.py`
- `docs/install.md`
- `docs/troubleshooting.md`

Locked files `scripts/bootstrap.sh` and `.env.example` were not changed.

## 3. Tests run and exact results

- `python3 -m pytest tests/test_config_validation.py -q`
  - PASS: `7 passed in 0.04s`
- `python3 scripts/validate-env.py --example .env.example`
  - PASS: `Config validation: 0 error(s), 0 warning(s); values were not printed.`
- `./scripts/check-secrets.sh`
  - PASS: `No obvious secrets detected by local regex scan.`
- `python3 -m py_compile scripts/validate-env.py services/api-gateway/app/config_validation.py services/api-gateway/app/main.py`
  - PASS
- `bash -n scripts/doctor-full.sh`
  - PASS
- `git diff --check`
  - PASS
- `python3 -m pytest tests -q`
  - FAIL: `5 failed, 192 passed, 2 skipped in 0.72s`
  - Three pre-existing failures are missing release scripts outside allowed scope:
    `scripts/release/build-android-signed.sh`,
    `scripts/release/publish-github-release.sh`, and
    `scripts/release/build-manifest.py`.
  - Two failures report `SettingsPage.vue` as orphaned because
    `apps/web/src/router/routes.ts` is outside the allowed edit scope.
- `PYTHONPATH=services/api-gateway python3 -m pytest services/api-gateway/tests -q`
  - BLOCKED during collection: local environment does not have `fastapi`
    installed (`ModuleNotFoundError: No module named 'fastapi'`).

## 4. Acceptance criteria status

- PASS: malformed URLs, ports, phone numbers, Twilio WhatsApp senders, OAuth
  redirect URIs, Azure config shapes, and AWS config shapes are detected.
- PASS: validator diagnostics do not print values; gateway settings mask
  secret-like values and no longer audit raw setting values.
- PASS: settings form masks secret fields, validates URL/port/phone/WhatsApp
  inputs, and shows restart guidance.
- PASS: unavailable optional upstream services return actionable HTTP 409
  details with `setup_path: /settings` instead of a raw gateway exception.
- PARTIAL: doctor prints actionable config diagnostics and incomplete optional
  groups are warnings. Locked `scripts/bootstrap.sh` could not be wired directly.
- BLOCKED: Settings page route registration requires editing
  `apps/web/src/router/routes.ts`, which is outside allowed scope.

## 5. Remaining risks

- Settings values are stored by the gateway, while existing optional services
  may still consume environment variables directly; applying saved values
  requires a separate runtime configuration integration.
- `SettingsPage.vue` is not reachable until its route is registered.
- Bootstrap does not call the validator because `scripts/bootstrap.sh` is locked.
- API gateway tests need the service Python dependencies installed.

## 6. Suggested follow-up tasks

- Allow a scoped route change to register `SettingsPage.vue`.
- Allow a scoped bootstrap change to run `validate-env.py` before Compose.
- Define and implement how saved gateway settings are propagated to optional
  services without exposing secrets.
- Restore the missing release scripts causing unrelated root-suite failures.
