# Task: intelligence-layer

Goal: add ethical public/user-authorized intelligence monitoring scaffold.

Allowed areas:
- `modules/intelligence/**`
- `services/intelligence-service/**`
- `apps/web/src/pages/IntelligencePage.vue`
- `apps/web/src/router/routes.ts`
- `infra/postgres/migrations/**`
- `docker-compose.yml`
- `tests/**`
- `docs/intelligence.md`

Allowed scope:
- public OSINT, RSS, web search via configured lawful providers, user-authorized OAuth sources.
- no interception, credential harvesting, paywall bypass, or unauthorized monitoring.

Acceptance:
- Intelligence route and module manifest exist.
- Source/keyword monitor scaffold exists.
- Structured source attribution.
- Save-to-Zettel/task hooks are present or clearly partial.
- Smoke test exists.


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

