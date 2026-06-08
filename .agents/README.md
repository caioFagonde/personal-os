# Personal OS AgentOps Swarm Kit

This kit coordinates multiple Claude Code and Codex workers without letting them trample the same files.

Core model:

```txt
Planner → task DAG → isolated git worktrees → bounded executors → verifier → human integration
```

It is intentionally conservative:

- every task runs in its own git worktree
- every task has allowed paths, locked paths, acceptance criteria, and tests
- no task may read or modify secrets/data/logs
- no auto-commit, auto-push, destructive commands, or paid cloud provisioning
- Claude/Codex can propose follow-up tasks, but the orchestrator dispatches them

Start with:

```bash
python3 scripts/agents/agentctl.py doctor
python3 scripts/agents/agentctl.py list
python3 scripts/agents/agentctl.py create-worktree ui-foundation
python3 scripts/agents/agentctl.py dispatch ui-foundation --engine claude --mode interactive
python3 scripts/agents/agentctl.py status
```

See `docs/agentops-swarm.md` for the full operating procedure.
