# backup-update-pipeline report

## Root cause / diagnosis

Connector backups were plaintext `.tar.gz` archives, Azure Blob and AWS S3 had no setup-state contract, and no update/preflight/rollback scripts guaranteed a backup before rebuilding. Update operations also had no ntfy progress hooks.

## Summary

- Enforced encrypted-only connector backup bundles using `BACKUP_ENCRYPTION_KEY`; missing or malformed keys fail safely and API exports return structured `409` setup guidance.
- Added `/api/connectors/backup/status` with Azure Blob and AWS S3 manual setup states, least-privilege credential guidance, and explicit no-paid-provisioning flags.
- Added backup-first preflight, safe update, explicit rollback, ntfy progress hooks, certification scripts, Make targets, UI setup states, and operator documentation.
- Preserved existing Google Drive and OneDrive encrypted upload actions.

## Files changed

- `services/connector-service/app/backup.py`
- `services/connector-service/app/main.py`
- `services/connector-service/tests/test_backup.py`
- `services/connector-service/tests/test_more_coverage.py`
- `scripts/preflight-update.sh`
- `scripts/update.sh`
- `scripts/rollback-last-update.sh`
- `scripts/certify/backup-smoke.sh`
- `scripts/certify/update-smoke.sh`
- `apps/web/src/pages/BackupRestorePage.vue`
- `apps/web/src/pages/ReleaseCenterPage.vue`
- `Makefile`
- `tests/test_backup_update_pipeline.py`
- `docs/backup.md`
- `docs/update-pipeline.md`
- `docs/cloud-provider-strategy.md`

## Tests run and exact results

- `./scripts/certify/backup-smoke.sh`: PASS (`3 passed`, then `4 passed`).
- `./scripts/certify/update-smoke.sh`: PASS (`4 passed`; shell syntax checks passed).
- `cd services/connector-service && python3 -m pytest tests/test_backup.py tests/test_more_coverage.py -q`: PASS (`12 passed`).
- `BACKUP_ENCRYPTION_KEY=test-only ./scripts/update.sh --dry-run`: PASS; printed encrypted backup request before both Docker rebuild/start commands.
- `git diff --check`: PASS.
- `python3 -m pytest tests -q`: PARTIAL/BASELINE FAIL (`249 passed, 2 skipped, 8 failed`). Failures are outside allowed task areas: missing API gateway optional-service contract, missing release scripts/tools, and existing Onboarding/Settings UI contract failures.
- `cd services/connector-service && python3 -m pytest tests -q`: BLOCKED at collection because `asyncpg` and `pytest-asyncio` are not installed in the current environment.
- `pnpm --dir apps/web build`: BLOCKED because `apps/web/node_modules` is absent; Quasar reported unknown `build` command from the global CLI.

## Acceptance criteria status

- Azure Blob backup setup state exists: PASS.
- AWS S3 backup setup state exists: PASS.
- Backups encrypted or encryption key clearly required: PASS; plaintext connector export is disabled.
- No root/broad cloud credentials requested: PASS; setup states and docs require container/bucket-scoped credentials.
- Update preflight backs up before rebuilding: PASS; certified and dry-run verified.
- ntfy progress hooks used when configured: PASS.
- No automatic paid provisioning: PASS; API states, UI, tests, and docs explicitly prohibit it.

## Remaining risks

- Azure Blob and AWS S3 currently expose safe setup states and strategy only; provider upload adapters are not implemented in this task.
- Restore tooling for `.tar.gz.enc` archives must use the same Fernet key; a dedicated encrypted restore workflow is still needed.
- Full connector and frontend build verification require project dependencies to be installed.

## Suggested follow-up tasks

- Implement explicit, dry-run-first Azure Blob and AWS S3 upload adapters using the documented least-privilege credentials.
- Add encrypted restore/decrypt verification and key-rotation tooling.
- Resolve the eight existing repository-suite failures and restore frontend dependency installation in CI.
