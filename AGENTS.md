# AGENTS.md — Personal OS Agent Rules for Codex and Other Coding Agents

Follow `CLAUDE.md`, `SKILLS.md`, and `.agents/active.json`.

Never read, print, edit, or commit:

- `.env`, `.env.*`
- `secrets/**`, `.private/**`
- `data/**`, `backups/**`, `logs/**`
- tokens, credentials, private keys, OAuth secrets, local personal data

Do not run destructive commands. Do not run `sudo`. Do not remove Docker volumes. Do not commit or push.

Use task-specific worktrees under `.agent-worktrees/`. Only edit paths listed in the task spec.

Every task must produce `.agents/reports/<task-id>/report.md` with tests and acceptance status.
