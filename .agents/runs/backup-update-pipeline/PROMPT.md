# Personal OS AgentOps Task: backup-update-pipeline

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/backup-update-pipeline
Branch: agent/backup-update-pipeline

## Role

# Role: DevOps Executor

Model: Codex or Sonnet. Mode: edit in a task-specific worktree.

Responsibilities:
- Fix scripts, Compose, CI/certification, config validation, backup/update flows.
- Validate commands non-destructively.
- Never delete volumes or secrets.
- Never auto-provision paid cloud resources.
- Add tests for every operational failure class.


## Task contract

# Task: backup-update-pipeline

Goal: Azure/AWS backup setup and safe update pipeline with ntfy progress.

Allowed areas:
- `scripts/update.sh`
- `scripts/preflight-update.sh`
- `scripts/rollback-last-update.sh`
- `scripts/certify/backup-smoke.sh`
- `scripts/certify/update-smoke.sh`
- `services/connector-service/**`
- `apps/web/src/pages/BackupRestorePage.vue`
- `apps/web/src/pages/ReleaseCenterPage.vue`
- `Makefile`
- `tests/**`
- `docs/backup.md`
- `docs/update-pipeline.md`
- `docs/cloud-provider-strategy.md`

Acceptance:
- Azure Blob and AWS S3 setup states exist.
- Backups are encrypted or clearly require encryption key setup.
- No root/broad cloud credentials requested.
- Update preflight backs up before rebuilding.
- ntfy progress hooks are used when configured.
- No automatic paid provisioning.


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
  "id": "backup-update-pipeline",
  "priority": "p1",
  "executor": "devops_executor",
  "title": "Azure/AWS backup provider setup and safe update pipeline with ntfy progress",
  "allowed_paths": [
    "scripts/update.sh",
    "scripts/preflight-update.sh",
    "scripts/rollback-last-update.sh",
    "scripts/certify/backup-smoke.sh",
    "scripts/certify/update-smoke.sh",
    "services/connector-service/**",
    "apps/web/src/pages/BackupRestorePage.vue",
    "apps/web/src/pages/ReleaseCenterPage.vue",
    "Makefile",
    "tests/**",
    "docs/backup.md",
    "docs/update-pipeline.md",
    "docs/cloud-provider-strategy.md"
  ],
  "locked_paths": [
    "Makefile",
    "scripts/update.sh"
  ],
  "depends_on": [
    "config-validation"
  ],
  "prompt_file": ".agents/tasks/backup-update-pipeline.md",
  "acceptance": [
    "Azure Blob backup setup state exists",
    "AWS S3 backup setup state exists",
    "No automatic paid provisioning",
    "Update preflight backs up before rebuild",
    "ntfy progress hooks are present when configured"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/certify/backup-smoke.sh",
    "./scripts/certify/update-smoke.sh"
  ]
}
```

## Required final report

Write a final report before stopping. Preferred location in the worktree:

`.agents/reports/backup-update-pipeline/report.md`

The controller will also collect it from:

`/home/caion/Documentos/github/personal-os-scaffold/personal-os/.agents/reports/backup-update-pipeline/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
