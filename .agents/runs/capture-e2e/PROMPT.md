# Personal OS AgentOps Task: capture-e2e

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/capture-e2e
Branch: agent/capture-e2e

## Role

# Role: Backend Executor

Model: Sonnet / Claude Code or Codex. Mode: edit in a task-specific worktree.

Responsibilities:
- Fix service endpoints, schemas, migrations, and backend tests for the task.
- Return structured expected errors, not raw 500s.
- Keep migrations idempotent.
- Never weaken auth or approval gates.
- Add smoke tests for repaired flows.


## Task contract

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



## Machine-readable task metadata

```json
{
  "id": "capture-e2e",
  "priority": "p0",
  "executor": "backend_executor",
  "title": "Fix capture, task creation, and secretary delegation end-to-end",
  "allowed_paths": [
    "services/capture-service/**",
    "services/api-gateway/**",
    "apps/web/src/pages/CapturePage.vue",
    "apps/web/src/pages/TasksPage.vue",
    "apps/web/src/services/api.ts",
    "infra/postgres/migrations/**",
    "tests/**",
    "scripts/certify/**",
    "docs/v1-feature-matrix.md"
  ],
  "locked_paths": [
    "services/capture-service/app/main.py",
    "apps/web/src/pages/CapturePage.vue"
  ],
  "depends_on": [],
  "prompt_file": ".agents/tasks/capture-e2e.md",
  "acceptance": [
    "Capture creates notes/tasks through gateway proxy",
    "Secretary missing channels returns structured 409 with setup action",
    "UI catches and renders API errors",
    "Non-destructive capture smoke script exists"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/check-secrets.sh",
    "./scripts/certify/v1-local-smoke.sh"
  ]
}
```

## Required final report

Write this file before stopping:

`.agents/reports/capture-e2e/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
