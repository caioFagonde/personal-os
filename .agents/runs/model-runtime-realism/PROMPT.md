# Personal OS AgentOps Task: model-runtime-realism

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/model-runtime-realism
Branch: agent/model-runtime-realism

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



## Machine-readable task metadata

```json
{
  "id": "model-runtime-realism",
  "priority": "p1",
  "executor": "backend_executor",
  "title": "Separate demo heuristics from real model providers and add setup/certification",
  "allowed_paths": [
    "services/model-runtime/**",
    "apps/web/src/pages/ModelRuntimePage.vue",
    "scripts/setup-models.sh",
    "scripts/certify/model-runtime-smoke.sh",
    "Makefile",
    "tests/**",
    "docs/model-runtime.md"
  ],
  "locked_paths": [
    "services/model-runtime/app/main.py",
    "apps/web/src/pages/ModelRuntimePage.vue"
  ],
  "depends_on": [
    "ui-foundation"
  ],
  "prompt_file": ".agents/tasks/model-runtime-realism.md",
  "acceptance": [
    "Heuristic mode clearly labeled demo-only",
    "Provider status endpoint reports installed/configured/tested",
    "Model setup docs/scripts exist",
    "No UI claims production model readiness without provider test"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/certify/model-runtime-smoke.sh"
  ]
}
```

## Required final report

Write a final report before stopping. Preferred location in the worktree:

`.agents/reports/model-runtime-realism/report.md`

The controller will also collect it from:

`/home/caion/Documentos/github/personal-os-scaffold/personal-os/.agents/reports/model-runtime-realism/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
