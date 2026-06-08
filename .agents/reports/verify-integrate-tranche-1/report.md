# Tranche 1 Integration Verification Report

**Date:** 2026-06-07
**Branch:** `agent/verify-integrate-tranche-1`
**Base:** `main` at `c7244c0` (after merging ui-foundation, capture-e2e, config-validation)

## 1. Merge state

All three tranche 1 branches merged cleanly into main in order:

| Branch | Commit | Merge commit |
|--------|--------|--------------|
| `agent/ui-foundation` | `2ac4dae` | `3bdba1f` |
| `agent/capture-e2e` | `16550b7` | `de70c0f` |
| `agent/config-validation` | `e29efbd` | `c7244c0` |

No merge conflicts detected. Working tree is clean.

## 2. Test results

```
python3 -m pytest tests -q
245 passed, 8 failed, 2 skipped (0.79s)
```

| Check | Result |
|-------|--------|
| `python3 -m pytest tests -q` | 245 passed, **8 failed**, 2 skipped |
| `python3 -m pytest tests/test_capture_e2e.py -v` | **11 passed** |
| `python3 -m pytest tests/test_config_validation.py -v` | 6 passed, **1 failed** |
| `python3 -m pytest tests/test_v1_productization.py -v` | 34 passed, **4 failed** |
| `./scripts/check-secrets.sh` | Pass — no secrets detected |
| `bash -n scripts/*.sh` | Pass — all scripts parse |
| `python3 scripts/validate-env.py --example .env.example` | Pass — 0 errors, 0 warnings |
| `docker compose --env-file .env.example --profile full config` | Fail — `.env` not present in worktree (expected; not a regression) |

## 3. Failure classification

### Pre-existing failures (3) — not caused by tranche 1

These were present before tranche 1 and noted in all three agent reports. The `scripts/release/` directory does not exist.

| Test | Missing file |
|------|-------------|
| `test_phase7_scaffold::test_release_manifest_tool_exists_and_is_executable` | `scripts/release/build-manifest.py` |
| `test_phase12_scaffold::test_phase12_device_and_release_scripts_are_present_and_executable` | `scripts/release/build-android-signed.sh` |
| `test_phase13_scaffold::test_phase13_certification_scripts_exist_and_are_executable` | `scripts/release/publish-github-release.sh` |

### Tranche 1 regressions (5) — introduced or unresolved by agent work

#### R1. `test_onboarding_uses_glass_card` (ui-foundation gap)

**Test expects:** `glass-card` class in `OnboardingPage.vue`
**Actual:** ui-foundation agent used `.nexus-stepper` with `background: var(--nexus-panel)` instead of `glass-card`.
**Severity:** Low — cosmetic consistency. Stepper has correct dark background.
**Fix:** Add `glass-card` class to `<q-stepper>` element in `OnboardingPage.vue`.

#### R2. `test_gateway_config_contract_is_actionable_and_redacted` (config-validation gap)

**Test expects:** `"optional_service_unavailable"` error code in `services/api-gateway/app/main.py`
**Actual:** The proxy handler at `main.py:611` returns `"service_unavailable"` code, not `"optional_service_unavailable"`. The config-validation agent did not add the specific error code.
**Severity:** Medium — tests expect a distinct error type for optional vs required service failures.
**Fix:** Add an `optional_service_unavailable` response path or rename the existing `service_unavailable` code in the proxy handler.

#### R3. `test_settings_page_has_validation` (config-validation gap)

**Test expects:** `:rules` and `E.164` directly in `SettingsPage.vue`
**Actual:** Validation lives in `NexusConfigForm.vue` (line 10: `:rules`, line 42: `E.164`), not SettingsPage itself. The config-validation agent correctly delegated validation to the shared form component, but the test checks the wrong file boundary.
**Severity:** Low — validation works correctly; the test assertion is too narrow.
**Fix:** Either update the test to check NexusConfigForm.vue, or re-export the validation markers in SettingsPage.

#### R4. `test_settings_page_has_save` (config-validation architectural mismatch)

**Test expects:** `localStorage` persistence in `SettingsPage.vue`
**Actual:** SettingsPage uses server-side persistence via `jsonFetch` PATCH to `/api/settings/{key}`. This is architecturally better (server-validated, encrypted, survives cache clears) but doesn't match the test's localStorage expectation.
**Severity:** Low — the test assumption is outdated given the server-side approach.
**Fix:** Update the test to check for `jsonFetch` or `apiUrl` instead of `localStorage`.

#### R5. `test_settings_page_has_service_health_check` (config-validation gap)

**Test expects:** `serviceStatus` or `checkServices` in `SettingsPage.vue`
**Actual:** SettingsPage has no service health check feature. The config-validation agent focused on validation and save, not health monitoring.
**Severity:** Medium — the Settings page should show service health as part of its diagnostic role.
**Fix:** Add a service health check section to SettingsPage that calls `/api/control/health`.

## 4. Per-agent assessment

### ui-foundation

**Status: Mostly complete**

- All acceptance criteria pass except OnboardingPage `glass-card` (R1).
- Dark theme overrides for stepper, tabs, chips, expansion items, toggle, separator, slider, dialog all present in `nexus-dark.scss`.
- Icon set correctly configured as `mdi-v7`.
- Overflow-x hidden on `.page-shell`.
- Shared components `NexusLoadingState`, `NexusErrorBanner`, `NexusPageHero` created and adopted.
- 34 of 38 productization tests pass.
- Config-validation agent's SettingsPage route was successfully registered (line 57 in `routes.ts`), correcting the config-validation report's claim that it was "BLOCKED".

**Remaining risk:** No visual verification was possible — all assertions are source-level. Dark theme pixel accuracy unconfirmed.

### capture-e2e

**Status: Complete**

- All 11 capture-e2e tests pass.
- WhatsApp provider default fixed (`"cloud_api"`).
- Debug file write removed.
- Structured 409 error for invalid delegation config working.
- UI error parsing in CapturePage and TasksPage working.

**No regressions introduced.**

### config-validation

**Status: Partially complete — 4 gaps remain**

- `validate-env.py` works: detects malformed URLs, ports, phones, redirects, Azure/AWS shapes.
- CLI never prints secret values (test passes).
- `doctor-full.sh` calls validator before compose (test passes).
- `NexusConfigForm.vue` masks secrets, validates E.164/URL/port, shows restart guidance (test passes).
- `config_validation.py` has `masked: "********"` and `setup_path: "/settings"` (test passes).
- SettingsPage route and navigation successfully registered (correcting the agent's report that this was BLOCKED).

**Gaps:**
- Missing `"optional_service_unavailable"` error code in `main.py` (R2).
- SettingsPage delegates validation to NexusConfigForm but tests expect it inline (R3).
- Server-side persistence vs. test's localStorage expectation (R4).
- No service health check in SettingsPage (R5).

## 5. Corrected agent report claims

The config-validation report stated:
> BLOCKED: Settings page route registration requires editing `apps/web/src/router/routes.ts`, which is outside allowed scope.

**This is incorrect.** The route IS registered at `routes.ts:57`:
```ts
{ path: '/settings', component: SettingsPage }
```
And the import is at line 28. The tests `test_settings_route_exists` and `test_settings_in_navigation` both PASS.

## 6. Follow-up tasks

### Must-fix (tranche 1 regressions)

1. **OnboardingPage glass-card** — Add `glass-card` class to `<q-stepper>` in `OnboardingPage.vue`
2. **optional_service_unavailable** — Add this error code to the proxy handler in `main.py` for optional service connection failures
3. **SettingsPage health check** — Add service health status section calling `/api/control/health`
4. **Test alignment for SettingsPage** — Update `test_settings_page_has_validation` and `test_settings_page_has_save` to match the actual (correct) architecture: validation in NexusConfigForm, persistence via API

### Pre-existing (not tranche 1 scope)

5. **Create `scripts/release/` directory** with `build-android-signed.sh`, `publish-github-release.sh`, `build-manifest.py` — fixes 3 pre-existing failures
6. **Bootstrap integration** — Wire `validate-env.py` into `scripts/bootstrap.sh`
7. **Visual QA** — Run dev server and screenshot all pages in dark theme on desktop/mobile viewports

## 7. Summary

Tranche 1 merged cleanly. Of 253 tests, 245 pass (96.8%). The 3 pre-existing failures are unchanged. The 5 new failures are all from test/implementation mismatches in config-validation (4) and a cosmetic gap in ui-foundation (1). Capture-e2e is fully clean. No data loss, no security regressions, no broken imports. The main follow-up work is aligning SettingsPage tests with the actual architecture and adding the missing `optional_service_unavailable` gateway error code.
