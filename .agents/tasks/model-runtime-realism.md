# Task: model-runtime-realism

Goal: distinguish demo heuristic fallbacks from real OCR/object/audio providers and add setup/certification.

Allowed areas:
- `services/model-runtime/**`
- `apps/web/src/pages/ModelRuntimePage.vue`
- `scripts/setup-models.sh`
- `scripts/certify/model-runtime-smoke.sh`
- `Makefile`
- `tests/**`
- `docs/model-runtime.md`

Acceptance:
- Heuristic mode is labeled demo-only.
- Real providers have installed/configured/tested states.
- No automatic large downloads without explicit consent.
- UI and certification distinguish demo from production readiness.


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

