You are the Tranche 04 QA and Repair node.

Run only after Tranche 04 implementation branches have been merged.

Read:
- .agentops/tasks/TRANCHE04_SHARED_CONTEXT.md
- .agentops/reports/TRANCHE_REPORT.md if present
- reports for all Tranche 04 workers if present

Mission:
Inspect and repair the integrated Tranche 04 implementation.

Scope:
- route/page correctness
- UI readability
- endpoint availability
- structured optional-service errors
- mobile responsive basics
- tests/certification scripts
- docs gaps

Check:
1. Routes and navigation
   - every sidebar/nav item resolves
   - every new route has a page
   - no blank pages
   - no broken imports

2. UI quality
   - no white-on-white panels
   - no pale text on white panels
   - no raw icon text artifacts like arrow_drop_down
   - no horizontal overflow on common desktop layout
   - mobile layout does not require dense tables

3. Endpoint behavior
   - UI-used endpoints exist
   - optional dependencies return structured unavailable/setup states
   - missing config never appears as raw 500 in normal flows

4. Feature continuity
   - offline queue visible
   - pairing visible
   - ntfy/Tailscale status visible
   - portable docs/scripts visible
   - AgentOps console visible if implemented

5. Tests
   - add missing route/static contract tests
   - add smoke scripts if missing
   - do not delete meaningful tests

Repair only bounded concrete issues. Do not add broad new features.

Acceptance:
- scripts/agents/run-pytest.sh tests -q passes
- ./scripts/check-secrets.sh passes
- pnpm --dir apps/web build passes if dependencies are installed
- docker compose config passes
- QA report written to .agentops/reports/qa-tranche4-route-endpoint-repair/report.md

Run:
scripts/agents/run-pytest.sh tests -q
./scripts/check-secrets.sh
pnpm --dir apps/web build
docker compose --env-file .env --profile full config >/tmp/personal-os-full.yml
