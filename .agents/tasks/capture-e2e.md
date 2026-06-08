# Task: capture-e2e

Goal: make Capture → Task/Note/Secretary delegation end-to-end reliable through the API gateway and UI.

Known failure class:
- UI button can call `/api/proxy/capture/api/capture` and receive raw 500 or unhandled errors.
- Missing secretary config should guide setup, not crash.

Allowed areas:
- `services/capture-service/**`
- `services/api-gateway/**`
- `apps/web/src/pages/CapturePage.vue`
- `apps/web/src/pages/TasksPage.vue`
- `apps/web/src/services/api.ts`
- `infra/postgres/migrations/**`
- `tests/**`
- `scripts/certify/**`
- `docs/v1-feature-matrix.md`

Acceptance:
- `/task Buy milk tomorrow` creates a task.
- `/note Some note` stores a note/capture.
- `/secretary ...` either queues delivery or returns structured 409 with setup action.
- UI catches all errors.
- Non-destructive smoke test exists.

Tests:
- `python3 -m pytest tests -q`
- `./scripts/check-secrets.sh`
- `./scripts/certify/v1-local-smoke.sh` if services are running


## Universal task rules

You are running inside a task-specific git worktree.

Do not read, print, edit, or commit:
- `.env`
- `.env.*`
- `secrets/**`
- `.private/**`
- `data/**`
- `backups/**`
- `logs/**`
- tokens, credentials, private keys, OAuth secrets, local personal data

Do not run destructive commands. Do not run `sudo`. Do not delete Docker volumes. Do not commit or push.

Before editing:
1. Inspect only relevant files.
2. State root cause.
3. State files to change.
4. State tests to run.

After editing, write `.agents/reports/{TASK_ID}/report.md` with:
1. Summary.
2. Files changed.
3. Tests run and results.
4. Acceptance status.
5. Remaining risks.
6. Suggested follow-up tasks.

