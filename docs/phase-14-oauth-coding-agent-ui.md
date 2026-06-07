# Phase 14: OAuth One-Click, Claude Code Remote Agent, Command Center UI

Phase 14 closes three daily-use gaps:

1. Connector onboarding no longer expects manual token copying. Google and Microsoft expose browser authorization plus a device-code fallback. Refresh credentials are encrypted server-side after consent.
2. Claude Code is wrapped behind a Personal OS coding-agent service. Jobs are queued from web/mobile, approval-gated, executed in isolated git worktrees, and run in dry-run mode by default.
3. The shell has a dedicated Command Center and a repaired dark visual system so cards, fields, tables, buttons, and dialogs remain legible on desktop and mobile.

## OAuth model

`.env` stores app credentials and redirect URIs. Encrypted refresh tokens are stored in Postgres, not copied into `.env`.

Supported flows:

- `/api/connectors/google/start`
- `/api/connectors/google/open`
- `/api/connectors/google/device/start`
- `/api/connectors/google/device/poll`
- `/api/connectors/microsoft/start`
- `/api/connectors/microsoft/open`
- `/api/connectors/microsoft/device/start`
- `/api/connectors/microsoft/device/poll`

## Coding agent

Default mode is safe dry-run:

```env
CODING_AGENT_EXECUTE=false
CLAUDE_CODE_COMMAND=claude
```

Enable actual Claude Code execution only after validating policies:

```env
CODING_AGENT_EXECUTE=true
```

All execution uses:

- repository allowlist
- prompt policy checks
- approval before execution
- git worktree isolation
- no raw remote shell endpoint
- secrets stripped from child process environment

## Routes

- `/` Command Center
- `/connectors` one-click OAuth/device-code onboarding
- `/coding-agent` remote Claude Code job queue

## Commands

```bash
make up-coding-agent
make test-phase14
```
