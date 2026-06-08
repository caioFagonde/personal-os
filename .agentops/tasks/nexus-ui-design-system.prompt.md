# AgentOps Task: nexus-ui-design-system

## Role
You are an implementation executor. Make focused, production-quality changes within the task scope. Add or update tests. Keep diffs coherent. Write a structured report.


## Framework Guidance
# vue-quasar guidance
- Keep changes scoped to allowed paths.
- Preserve existing public contracts unless the task explicitly changes them.
- Add tests or smoke checks that prove the acceptance criteria.
- Do not hide failures with broad skips.


## Task
Title: Nexus Big Picture design system foundation
Priority: p0
Executor: claude

## Allowed paths
[
  "apps/web/src/css",
  "apps/web/src/components",
  "apps/web/src/layouts",
  "apps/web/src/router",
  "apps/web/src/pages",
  "apps/web/src/services",
  "tests",
  "docs",
  ".agentops/examples"
]

## Locked paths
[
  "apps/web/src/css/app.scss",
  "apps/web/src/components/nexus",
  "apps/web/src/layouts/MainLayout.vue"
]

## Acceptance criteria
[
  "Global dark/glass theme is legible and consistent",
  "No white-on-white or pale text on white panels",
  "Reusable Nexus UI components exist for hero, glass card, carousel, status pill, action tile, empty state, and loading state",
  "Horizontal overflow is eliminated at desktop and mobile widths",
  "Existing routes still compile",
  "pnpm web build passes"
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
- Write a report to `.agentops/reports/nexus-ui-design-system/report.md` before finishing.

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
