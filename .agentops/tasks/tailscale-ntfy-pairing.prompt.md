# AgentOps Task: tailscale-ntfy-pairing

## Role
You are an implementation executor. Make focused, production-quality changes within the task scope. Add or update tests. Keep diffs coherent. Write a structured report.


## Framework Guidance
# fastapi guidance
- Keep changes scoped to allowed paths.
- Preserve existing public contracts unless the task explicitly changes them.
- Add tests or smoke checks that prove the acceptance criteria.
- Do not hide failures with broad skips.


## Task
Title: Phone pairing, Tailscale private URL, and ntfy notification setup
Priority: p0
Executor: claude

## Allowed paths
[
  "apps/web/src/pages",
  "apps/web/src/components",
  "apps/web/src/services",
  "services/api-gateway",
  "services/notification-gateway",
  "services/connector-service",
  "scripts",
  "docs",
  "tests"
]

## Locked paths
[
  "apps/web/src/pages/PairDevicePage.vue",
  "apps/web/src/pages/ConnectorsPage.vue",
  "scripts/onboarding"
]

## Acceptance criteria
[
  "Pair Device page clearly shows local URL and Tailscale/private URL when detectable",
  "QR pairing UX is clear and safe",
  "ntfy setup has subscribe/test/dry-run states",
  "Missing Tailscale or ntfy config shows setup guidance, not raw error",
  "No automatic public exposure is introduced",
  "Tests cover pairing/config contracts"
]

## Checks
[
  "scripts/agents/run-pytest.sh tests -q",
  "./scripts/check-secrets.sh",
  "docker compose --env-file .env --profile full config >/tmp/personal-os-full.yml"
]

## Safety
- Do not read, print, modify, or commit .env, .env.*, secrets/, credentials, tokens, private keys, backups/, data/, logs/, or personal data.
- Do not perform destructive actions.
- Do not push to remote.
- Keep changes bounded to the task.
- Write a report to `.agentops/reports/tailscale-ntfy-pairing/report.md` before finishing.

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
