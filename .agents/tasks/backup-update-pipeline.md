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

