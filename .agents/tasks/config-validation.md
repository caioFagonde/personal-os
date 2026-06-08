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

