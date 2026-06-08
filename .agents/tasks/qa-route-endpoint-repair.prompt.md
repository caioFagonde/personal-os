You are the QA and repair node for Personal OS.

Read CLAUDE.md and SKILLS.md. Obey all security rules.

Task:
After tranche 3 implementation branches are merged, inspect every route and UI-used endpoint, run non-destructive checks, repair concrete failures, and generate a QA report.

Do not add broad new features.
Do not read .env contents.
Do not read secrets, data, backups, logs, tokens, credentials, or private keys.
You may use `.env` only as `--env-file .env` for docker compose.
Do not run destructive endpoints or external sends.
Do not send real Twilio/email/cloud operations.

Inspect:
- apps/web/src/router/routes.ts
- apps/web/src/pages/*
- apps/web/src/services/api.ts
- services/*/app/main.py
- scripts/certify/*
- docker-compose.yml
- docs/v1-feature-matrix.md if present

Check:
- every route has a page
- every nav link resolves
- every key page has loading/error/empty states
- every UI-used backend endpoint exists or is marked partial
- no expected config issue returns raw 500
- no pages have obvious broken icon/text patterns
- no route silently blank
- smoke scripts cover major endpoints

Implement repairs only when concrete and bounded.

Add or update:
- scripts/certify/v1-local-smoke.sh
- scripts/certify/ui-local-smoke.sh
- tests for route/endpoint contracts
- docs/v1-feature-matrix.md if needed

Run:
python3 -m pytest tests -q
./scripts/check-secrets.sh
docker compose --env-file .env --profile full config
pnpm --dir apps/web build || true

If Docker is running:
docker compose --env-file .env ps || true

Write report to:
.agents/reports/qa-route-endpoint-repair/report.md
