You are the Tranche 04 AgentOps Console worker.

Read:
- .agentops/tasks/TRANCHE04_SHARED_CONTEXT.md

Mission:
Bring the AgentOps swarm into Personal OS as a visible control surface.

Implement:
1. AgentOps page
   - task list
   - branch/worktree status
   - reports summary
   - event log summary
   - budget/time summary if available
   - model availability cards for Claude Code, Codex, Antigravity

2. Safety UX
   - show allowed paths before execution
   - show branch/worktree isolation
   - no automatic merge/push from UI
   - destructive actions require explicit approval

3. Integration contracts
   - read local AgentOps JSON/report files through safe backend endpoint if existing pattern supports it
   - otherwise implement UI scaffold with clear "local agentops files unavailable" state
   - do not expose secrets or raw local filesystem browsing

4. Coding Agent relationship
   - link to Coding Agent page
   - distinguish "agentops local swarm" from "remote command bus"
   - dry-run execution only unless approved

5. Tests
   - route exists
   - cards/status states render
   - missing local files handled gracefully

Do not:
- implement arbitrary unauthenticated shell execution
- expose full filesystem
- merge/push from UI
- print secrets

Acceptance:
- AgentOps control page exists
- Reports/status are understandable
- Claude/Codex/Antigravity status is visible
- Safety boundaries are explicit
- Report written to .agentops/reports/agentops-console-in-personal-os/report.md

Run:
scripts/agents/run-pytest.sh tests -q
./scripts/check-secrets.sh
pnpm --dir apps/web build
