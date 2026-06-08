You are the Tranche 04 Big Picture Command Center worker.

Read:
- .agentops/tasks/TRANCHE04_SHARED_CONTEXT.md
- .agentops/examples/GENERATED_INDEX.md
- .agentops/examples/markdown/tranche04-ui-reference.md

Mission:
Transform the main Personal OS interface into a cinematic, intuitive command cockpit inspired by console/Big Picture UI patterns.

Primary pages:
- Command Center
- Main layout shell
- module navigation surfaces
- route launcher UX

Implement:
1. Big Picture Command Center
   - large focused module carousel
   - recent activity/action rail
   - daily command cards
   - system health/status card
   - quick capture card
   - sync/backup/agent status surfaces

2. Navigation model
   - desktop: sidebar + central cockpit
   - mobile: compact command deck
   - keyboard-friendly focus affordances
   - no dead nav links

3. Visual style
   - floating glass cards
   - readable text
   - abstract local background/gradient
   - no third-party images
   - no white panels unless intentionally themed and readable

4. Feedback
   - loading state
   - empty state
   - error state
   - unavailable/setup state

5. Tests
   - page existence/route contracts
   - static UI contract checks where useful

Do not:
- break existing pages
- remove module links
- hardcode private data
- use copyrighted images as assets

Acceptance:
- Command Center feels like a central cockpit, not a table dashboard
- Horizontal carousel/module rail exists
- Cards are readable
- Mobile layout is usable
- No route silently blanks
- Report written to .agentops/reports/nexus-big-picture-command-center/report.md

Run:
scripts/agents/run-pytest.sh tests -q
./scripts/check-secrets.sh
pnpm --dir apps/web build
