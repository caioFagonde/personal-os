# Personal OS AgentOps Task: config-validation

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/config-validation
Branch: agent/config-validation

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

# Task: config-validation

Goal: catch missing/malformed config early and surface guided setup instead of runtime failures.

Allowed areas:
- `scripts/validate-env.py`
- `scripts/bootstrap.sh`
- `scripts/doctor-full.sh`
- `apps/web/src/pages/SettingsPage.vue`
- `apps/web/src/components/NexusConfigForm.vue`
- `services/api-gateway/**`
- `.env.example`
- `tests/**`
- `docs/install.md`
- `docs/troubleshooting.md`

Acceptance:
- malformed URLs, ports, phone numbers, Twilio WhatsApp senders, OAuth redirect URIs, Azure/AWS config shapes are detected.
- no secret value is printed.
- Settings UI has masks/validation and restart guidance.
- bootstrap reports config warnings without failing optional services.

Tests:
- `python3 -m pytest tests -q`
- `./scripts/check-secrets.sh`
- `python3 scripts/validate-env.py --example .env.example`


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
  "id": "config-validation",
  "priority": "p0",
  "executor": "devops_executor",
  "title": "Add safe env/runtime config validation and settings setup UX contracts",
  "allowed_paths": [
    "scripts/validate-env.py",
    "scripts/bootstrap.sh",
    "scripts/doctor-full.sh",
    "apps/web/src/pages/SettingsPage.vue",
    "apps/web/src/components/NexusConfigForm.vue",
    "services/api-gateway/**",
    ".env.example",
    "tests/**",
    "docs/install.md",
    "docs/troubleshooting.md"
  ],
  "locked_paths": [
    "scripts/bootstrap.sh",
    ".env.example"
  ],
  "depends_on": [],
  "prompt_file": ".agents/tasks/config-validation.md",
  "acceptance": [
    "Malformed config is caught without printing secret values",
    "Settings page validates masked fields",
    "Missing optional config routes to setup UI not raw 500",
    "Bootstrap prints actionable config diagnostics"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/check-secrets.sh",
    "python3 scripts/validate-env.py --example .env.example"
  ]
}
```

## Required final report

Write this file before stopping:

`.agents/reports/config-validation/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
