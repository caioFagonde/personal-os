# Obsidian / Notion / Trello connector report

Date: 2026-06-08

## Summary

Implemented safe connector skeletons and marketplace UX for Obsidian, Notion, and Trello.

- Added provider status, configuration metadata, capabilities, and structured missing-configuration contracts without exposing configured values.
- Added Obsidian relative Markdown path validation, traversal/symlink escape rejection, dry-run import/export, explicit contained export, and no-overwrite behavior.
- Added Notion dry-run page creation and structured Markdown export contracts. External execution is rejected.
- Added Trello dry-run card creation contract. External execution is rejected.
- Added setup cards and dry-run actions to the Connectors marketplace UI. No provider secrets are stored in browser localStorage.
- Added Markdown/Zettelkasten compatibility and connector contract documentation.

## Endpoints

- `GET /api/connectors/{provider}/setup/status`
- `POST /api/connectors/obsidian/path/validate`
- `POST /api/connectors/obsidian/export`
- `POST /api/connectors/obsidian/import`
- `POST /api/connectors/notion/pages/dry-run`
- `POST /api/connectors/notion/export/dry-run`
- `POST /api/connectors/trello/cards/dry-run`

## Tests

- PASS: `python3 -m pytest tests/test_providers.py -q` from `services/connector-service` (`7 passed`)
- PASS: `python3 -m pytest tests/test_obsidian_notion_trello_connectors.py tests/test_phase13_15_connector_oauth_ui_regression.py -q` (`7 passed`)
- PASS: `python3 -m py_compile services/connector-service/app/main.py services/connector-service/app/providers.py`
- PASS: `git diff --check`
- PASS: `./scripts/check-secrets.sh`
- PARTIAL: `python3 -m pytest tests -q` (`254 passed, 2 skipped, 8 failed`)

The eight root-suite failures are in unrelated existing gateway configuration, release-script, onboarding, and settings contracts outside this task's allowed scope.

- BLOCKED: `docker compose --env-file .env --profile full config`

The isolated worktree has no `.env`; Compose exited with `couldn't find env file`. No environment file was inspected or printed.

- BLOCKED: `pnpm --dir apps/web build`

The worktree has no `node_modules`, so the local Quasar build command is unavailable.

- BLOCKED: full `services/connector-service` test suite

The local Python environment lacks the existing `asyncpg` dependency. The focused provider tests do not require it and pass.

## Acceptance

- PASS: Obsidian, Notion, and Trello appear in connector/marketplace UI.
- PASS: Missing configuration is structured.
- PASS: Dry-run paths exist and external writes are disabled by default.
- PASS: Obsidian writes are constrained to validated Markdown paths inside the configured vault and refuse overwrite.
- PASS: Connector-focused tests pass.
- PARTIAL: Repository-wide tests do not fully pass because of eight unrelated failures listed above.
- PASS: Required report written.
