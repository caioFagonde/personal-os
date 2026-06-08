# Personal OS AgentOps Task: maps-geolocation

Repository root: /home/caion/Documentos/github/personal-os-scaffold/personal-os
Worktree path: /home/caion/Documentos/github/personal-os-scaffold/personal-os/.agent-worktrees/maps-geolocation
Branch: agent/maps-geolocation

## Role

# Role: UI Executor

Model: Sonnet / Claude Code. Mode: edit in a task-specific worktree.

Responsibilities:
- Fix only the task-scoped UI files.
- Use shared Nexus components and design tokens.
- Add loading/empty/error/success states.
- Remove unhandled Promise rejections.
- Fix responsiveness and readability.
- Add tests or scaffold guards.

Do not touch backend, migrations, Docker, or bootstrap unless the task explicitly allows it.


## Task contract

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



## Machine-readable task metadata

```json
{
  "id": "maps-geolocation",
  "priority": "p1",
  "executor": "ui_executor",
  "title": "Implement automatic coordinates and honest maps/AR setup flow",
  "allowed_paths": [
    "apps/web/src/pages/GeospatialPage.vue",
    "apps/web/src/pages/ARMemoryPage.vue",
    "apps/web/src/components/**",
    "services/module-service/**",
    "scripts/maps/**",
    "scripts/certify/maps-smoke.sh",
    "tests/**",
    "docs/maps.md"
  ],
  "locked_paths": [
    "apps/web/src/pages/GeospatialPage.vue",
    "apps/web/src/pages/ARMemoryPage.vue"
  ],
  "depends_on": [
    "ui-foundation"
  ],
  "prompt_file": ".agents/tasks/maps-geolocation.md",
  "acceptance": [
    "Use current location button via browser Geolocation",
    "Permission denied shows manual fallback",
    "Map data missing has setup state",
    "Coordinate validation exists"
  ],
  "tests": [
    "python3 -m pytest tests -q",
    "./scripts/certify/maps-smoke.sh"
  ]
}
```

## Required final report

Write a final report before stopping. Preferred location in the worktree:

`.agents/reports/maps-geolocation/report.md`

The controller will also collect it from:

`/home/caion/Documentos/github/personal-os-scaffold/personal-os/.agents/reports/maps-geolocation/report.md`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
