# Task: maps-geolocation

Goal: make Maps/AR coordinates automatic and maps honest about missing data.

Allowed areas:
- `apps/web/src/pages/GeospatialPage.vue`
- `apps/web/src/pages/ARMemoryPage.vue`
- `apps/web/src/components/**`
- `services/module-service/**`
- `scripts/maps/**`
- `scripts/certify/maps-smoke.sh`
- `tests/**`
- `docs/maps.md`

Acceptance:
- Use current location button uses browser Geolocation API.
- Permission denied shows manual fallback.
- Coordinates validated.
- TileServer/map-data missing shows setup flow.
- AR page shows orientation/geolocation capability states honestly.


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

