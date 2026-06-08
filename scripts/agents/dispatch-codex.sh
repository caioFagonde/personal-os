#!/usr/bin/env bash
set -Eeuo pipefail

TASK="${1:?task id required}"
MODE="${2:-interactive}"
PERMISSION_MODE="${3:-workspace}" # workspace | full

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WT="$ROOT/.agent-worktrees/$TASK"
PROMPT_FILE="$ROOT/.agents/tasks/$TASK.prompt.md"

[[ -d "$WT" ]] || {
  echo "Missing worktree: $WT"
  echo "Run: python3 scripts/agents/agentctl.py create-worktree $TASK"
  exit 1
}

[[ -f "$PROMPT_FILE" ]] || {
  echo "Missing prompt: $PROMPT_FILE"
  exit 1
}

if [[ "$MODE" == "interactive" ]]; then
  echo "Starting Codex interactive TUI."
  echo "Task: $TASK"
  echo "Worktree: $WT"
  echo "Prompt file: $PROMPT_FILE"
  echo
  echo "Inside Codex, paste:"
  echo "Read and execute the task prompt at: $PROMPT_FILE"
  echo
  if [[ "$PERMISSION_MODE" == "full" ]]; then
    codex --dangerously-bypass-approvals-and-sandbox --cd "$WT"
  else
    codex --sandbox workspace-write --cd "$WT"
  fi
else
  PROMPT="$(cat "$PROMPT_FILE")"
  if [[ "$PERMISSION_MODE" == "full" ]]; then
    codex exec --dangerously-bypass-approvals-and-sandbox --cd "$WT" "$PROMPT"
  else
    codex exec --sandbox workspace-write --cd "$WT" "$PROMPT"
  fi
fi
