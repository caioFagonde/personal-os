# Personal OS AgentOps Task: verify-integrate-tranche-1

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/verify-integrate-tranche-1
Branch: agent/verify-integrate-tranche-1

## Role

# Role: Verifier Node

Model: Codex/Sonnet. Mode: read/test preferred.

Responsibilities:
- Run assigned tests.
- Inspect diffs for scope creep and secret-path violations.
- Verify acceptance criteria.
- Produce a merge recommendation.
- Create remediation nodes for concrete failures.

Do not perform broad implementation changes unless explicitly assigned a remediation task.


## Task contract

# Task: verify-integrate-tranche-1

Goal: verify and recommend integration order for first tranche.

Inputs:
- `.agents/reports/ui-foundation/report.md`
- `.agents/reports/capture-e2e/report.md`
- `.agents/reports/config-validation/report.md`
- branch diffs
- test results

Do not add broad features. You may add narrow regression tests only if necessary to prove a concrete failure.

Acceptance:
- each p0 task has report
- branch diffs are scoped
- no secret path changed
- tests run or exact blockers documented
- merge order and risk noted


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
  "id": "verify-integrate-tranche-1",
  "priority": "p0",
  "executor": "verifier",
  "title": "Verify and integrate first tranche: UI foundation, capture, config validation",
  "allowed_paths": [
    "tests/**",
    ".agents/reports/**",
    "docs/v1-feature-matrix.md"
  ],
  "locked_paths": [],
  "depends_on": [
    "ui-foundation",
    "capture-e2e",
    "config-validation"
  ],
  "prompt_file": ".agents/tasks/verify-integrate-tranche-1.md",
  "acceptance": [
    "Reports exist for all p0 tasks",
    "Tests run or exact blockers documented",
    "Merge order recommended",
    "No secret-path changes"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/check-secrets.sh",
    "docker compose --env-file .env --profile full config"
  ]
}
```

## Required final report

Write a final report before stopping. Preferred location in the worktree:

`.agents/reports/verify-integrate-tranche-1/report.md`

The controller will also collect it from:

`/home/caion/Documentos/github/personal-os-scaffold/personal-os/.agents/reports/verify-integrate-tranche-1/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
