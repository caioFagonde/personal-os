# AgentOps Swarm Operating Guide

## Purpose

This is a local, human-supervised multi-agent workflow for Personal OS. It coordinates Claude Code and Codex without letting autonomous workers overwrite each other or access secrets.

Claude Code is a terminal coding agent that can edit files, run commands, and be used in non-interactive `-p` mode. Codex CLI is OpenAI's local coding agent and supports both interactive work and `codex exec` for non-interactive tasks. Use both under worktree isolation and approval gates.

## Safety model

Agents may propose work. The orchestrator dispatches work. The integrator merges work. The human approves destructive or external side effects.

Forbidden to all workers:

- `.env`, `.env.*`
- `secrets/**`, `.private/**`
- `data/**`, `backups/**`, `logs/**`
- tokens, credentials, private keys, OAuth secrets, local personal data
- `sudo`, Docker volume deletion, force-push, paid cloud provisioning

## Install this kit

From repo root:

```bash
unzip /path/to/personal-os-agentops-swarm-kit.zip -d /tmp/agentops-kit
rsync -a /tmp/agentops-kit/personal-os/ ./
python3 scripts/agents/agentctl.py doctor
```

## Recommended first tranche

Do not run every task at once. Start with three P0 workers:

```bash
python3 scripts/agents/agentctl.py create-worktree ui-foundation
python3 scripts/agents/agentctl.py create-worktree capture-e2e
python3 scripts/agents/agentctl.py create-worktree config-validation
```

Open three terminals:

```bash
scripts/agents/dispatch-claude.sh ui-foundation interactive
scripts/agents/dispatch-claude.sh capture-e2e interactive
scripts/agents/dispatch-codex.sh config-validation interactive
```

Open a fourth monitor terminal:

```bash
scripts/agents/monitor.sh
```

## Headless mode

Use only for tightly scoped tasks. Interactive mode is safer for high-impact changes.

```bash
python3 scripts/agents/agentctl.py dispatch ui-foundation --engine claude --mode headless
python3 scripts/agents/agentctl.py dispatch config-validation --engine codex --mode headless
```

## Worktree layout

```txt
.agent-worktrees/
  ui-foundation/
  capture-e2e/
  config-validation/
.agents/runs/<task-id>/PROMPT.md
.agents/reports/<task-id>/report.md
```

## Monitoring

```bash
python3 scripts/agents/agentctl.py status
python3 scripts/agents/agentctl.py diff ui-foundation
python3 scripts/agents/agentctl.py collect
```

Reports are collected into:

```txt
.agents/reports/TRANCHE_REPORT.md
```

## Integration sequence

Merge one branch at a time.

```bash
git status
python3 scripts/agents/agentctl.py diff ui-foundation
git merge --no-ff agent/ui-foundation
python3 -m pytest tests -q
./scripts/check-secrets.sh
pnpm --dir apps/web build
```

Then repeat for the next branch. If a merge fails, stop and create a remediation task. Do not merge multiple agent branches blindly.

## Replanning

After every tranche:

1. collect reports
2. run tests
3. classify failures
4. update `.agents/active.json`
5. dispatch the next 1–4 tasks

## Recommended model roles

- Planner: Opus or GPT high-reasoning model, read-only
- Scout: Haiku, read-only inventory
- UI executor: Sonnet / Claude Code
- Backend executor: Sonnet / Claude Code
- DevOps executor: Codex or Sonnet
- Verifier: Codex or Sonnet, test-focused
- Integrator: Opus/GPT + human

## One-hour cadence

A one-hour tranche should produce a mergeable subsystem improvement, not a complete OS rewrite:

```txt
0–5 min: select tasks
5–45 min: workers execute
45–60 min: collect reports, run tests, integrate/replan
```

Maximum parallel workers: 3–4.


## Reports and integration notes

Interactive agents often write reports inside their own worktree. Run:

```bash
python3 scripts/agents/agentctl.py collect
cat .agents/reports/TRANCHE_REPORT.md
```

The collector searches both the controller repo and each worktree.

`git merge agent/<task>` only merges committed changes. If an agent changed files
but you see `Already up to date`, inspect the worktree and commit or patch it:

```bash
git -C .agent-worktrees/<task-id> status --short
git -C .agent-worktrees/<task-id> diff --stat
```

Then either commit from inside the worktree:

```bash
cd .agent-worktrees/<task-id>
git add <changed-files>
git commit -m "Agent task: <task-id>"
cd ../..
git merge --no-ff agent/<task-id>
```

or export a patch:

```bash
git -C .agent-worktrees/<task-id> diff > /tmp/<task-id>.patch
git apply /tmp/<task-id>.patch
```
