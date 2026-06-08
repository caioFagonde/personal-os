# Task: ui-foundation

Goal: fix the global Nexus UI foundation: dark theme, icon rendering, page layout, overflow, shared components.

Allowed areas:
- `apps/web/src/css/**`
- `apps/web/src/design/**`
- `apps/web/src/components/**`
- `apps/web/src/pages/**`
- `apps/web/src/router/**`
- `apps/web/quasar.config.ts`
- `apps/web/index.html`
- `tests/**`
- `docs/ux-command-center.md`

Acceptance:
- no unreadable white cards/forms in dark theme
- no broken icon text artifacts such as `arrow_drop_down`
- no global horizontal overflow on core pages
- primary buttons visible and aligned
- core pages use consistent Nexus components
- shared loading/empty/error states exist

Focus first on visible failures:
- StudyPage, ResearchPage, GeospatialPage, ARMemoryPage, AutomationPage, ZettelkastenPage, ConnectorsPage, OnboardingPage, ModelRuntimePage

Tests:
- `python3 -m pytest tests -q`
- `./scripts/check-secrets.sh`
- `pnpm --dir apps/web build` if dependencies are available


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

