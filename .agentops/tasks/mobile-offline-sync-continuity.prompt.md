# AgentOps Task: mobile-offline-sync-continuity

## Role
You are an implementation executor. Make focused, production-quality changes within the task scope. Add or update tests. Keep diffs coherent. Write a structured report.


## Framework Guidance
# vue-quasar guidance
- Keep changes scoped to allowed paths.
- Preserve existing public contracts unless the task explicitly changes them.
- Add tests or smoke checks that prove the acceptance criteria.
- Do not hide failures with broad skips.


## Task
Title: Mobile offline queue and sync continuity UX
Priority: p0
Executor: claude

## Allowed paths
[
  "apps/web/src/pages",
  "apps/web/src/components",
  "apps/web/src/services",
  "apps/mobile",
  "services/sync-engine",
  "services/api-gateway",
  "tests",
  "docs"
]

## Locked paths
[
  "apps/web/src/pages/OfflineQueuePage.vue",
  "apps/web/src/pages/SyncHealthPage.vue"
]

## Acceptance criteria
[
  "Mobile-first offline queue UI exists",
  "Capture/tasks can queue offline mutations conceptually or through existing service contracts",
  "Sync state, retry state, conflict state, and pending count are visible",
  "No failed network call crashes the UI",
  "Empty states and setup actions exist",
  "Tests cover offline queue contracts"
]

## Checks
[
  "scripts/agents/run-pytest.sh tests -q",
  "./scripts/check-secrets.sh",
  "pnpm --dir apps/web build"
]

## Safety
- Do not read, print, modify, or commit .env, .env.*, secrets/, credentials, tokens, private keys, backups/, data/, logs/, or personal data.
- Do not perform destructive actions.
- Do not push to remote.
- Keep changes bounded to the task.
- Write a report to `.agentops/reports/mobile-offline-sync-continuity/report.md` before finishing.

## Examples / reference material
If `.agentops/examples/GENERATED_INDEX.md` exists, read it and inspect only relevant example files. Use visual/material examples as inspiration/specification, not as copied assets unless the user owns them.

## Final report format
Write:
- status
- root cause / implementation summary
- files changed
- tests run
- results
- risks
- follow-up tasks
