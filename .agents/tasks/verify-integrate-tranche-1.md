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

