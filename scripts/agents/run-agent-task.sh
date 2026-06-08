#!/usr/bin/env bash
set -Eeuo pipefail

TASK="${1:?task id required}"
ENGINE="${2:?engine required: claude|codex}"
MODE="${3:-headless}"          # headless | interactive
PERMISSION="${4:-full}"        # workspace | full

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WT="$ROOT/.agent-worktrees/$TASK"
PROMPT_FILE="$ROOT/.agents/tasks/$TASK.prompt.md"

cd "$ROOT"

[[ -d "$WT" ]] || {
  echo "Missing worktree: $WT"
  echo "Run: python3 scripts/agents/agentctl.py create-worktree $TASK"
  read -r -p "Press Enter to close..."
  exit 1
}

[[ -f "$PROMPT_FILE" ]] || {
  echo "Missing prompt file: $PROMPT_FILE"
  read -r -p "Press Enter to close..."
  exit 1
}

cd "$WT"
mkdir -p ".agents/reports/$TASK"

echo "===== Agent task: $TASK ====="
echo "Engine:     $ENGINE"
echo "Mode:       $MODE"
echo "Permission: $PERMISSION"
echo "Worktree:   $WT"
echo "Prompt:     $PROMPT_FILE"
echo

run_claude_headless() {
  local prompt_text
  prompt_text="$(cat "$PROMPT_FILE")"

  if [[ "$PERMISSION" == "full" ]]; then
    if claude --help 2>&1 | grep -q -- '--permission-mode'; then
      claude --permission-mode bypassPermissions -p "$prompt_text"
    else
      claude --dangerously-skip-permissions -p "$prompt_text"
    fi
  else
    claude -p "$prompt_text"
  fi
}

run_claude_interactive() {
  echo "Starting Claude Code interactive TUI."
  echo
  echo "Paste this instruction inside Claude:"
  echo "Read and execute the task prompt at: $PROMPT_FILE"
  echo
  if [[ "$PERMISSION" == "full" ]]; then
    if claude --help 2>&1 | grep -q -- '--permission-mode'; then
      claude --permission-mode bypassPermissions
    else
      claude --dangerously-skip-permissions
    fi
  else
    claude
  fi
}

run_codex_headless() {
  local prompt_text
  prompt_text="$(cat "$PROMPT_FILE")"

  echo "Codex version:"
  codex --version || true
  echo

  if [[ "$PERMISSION" == "full" ]]; then
    codex exec \
      --dangerously-bypass-approvals-and-sandbox \
      --cd "$WT" \
      "$prompt_text"
  else
    codex exec \
      --sandbox workspace-write \
      --cd "$WT" \
      "$prompt_text"
  fi
}

run_codex_interactive() {
  echo "Starting Codex interactive TUI."
  echo
  echo "Paste this instruction inside Codex:"
  echo "Read and execute the task prompt at: $PROMPT_FILE"
  echo

  if [[ "$PERMISSION" == "full" ]]; then
    codex \
      --dangerously-bypass-approvals-and-sandbox \
      --cd "$WT"
  else
    codex \
      --sandbox workspace-write \
      --cd "$WT"
  fi
}

RC=0

if [[ "$ENGINE" == "claude" && "$MODE" == "headless" ]]; then
  run_claude_headless || RC=$?
elif [[ "$ENGINE" == "claude" && "$MODE" == "interactive" ]]; then
  run_claude_interactive || RC=$?
elif [[ "$ENGINE" == "codex" && "$MODE" == "headless" ]]; then
  run_codex_headless || RC=$?
elif [[ "$ENGINE" == "codex" && "$MODE" == "interactive" ]]; then
  run_codex_interactive || RC=$?
else
  echo "Invalid engine/mode: $ENGINE / $MODE"
  RC=2
fi

mkdir -p ".agents/reports/$TASK"

if [[ "$RC" -ne 0 ]]; then
  {
    echo "# $TASK report"
    echo
    echo "Status: FAILED"
    echo
    echo "Agent command exited with code $RC."
    echo
    echo "## Git status"
    git status --short || true
    echo
    echo "## Diff stat"
    git diff --stat || true
  } > ".agents/reports/$TASK/report.md"

  echo
  echo "===== $TASK FAILED with exit code $RC ====="
  cat ".agents/reports/$TASK/report.md"
  echo
  read -r -p "Press Enter to close..."
  exit "$RC"
fi

if [[ ! -f ".agents/reports/$TASK/report.md" ]]; then
  {
    echo "# $TASK report"
    echo
    echo "Status: COMPLETED_WITHOUT_EXPLICIT_REPORT"
    echo
    echo "Agent completed but did not write a structured report."
    echo
    echo "## Git status"
    git status --short || true
    echo
    echo "## Diff stat"
    git diff --stat || true
  } > ".agents/reports/$TASK/report.md"
fi

if git status --short | grep -q .; then
  git add .
  git commit -m "Agent task: $TASK"
else
  echo "No changes to commit for $TASK"
fi

echo
echo "===== $TASK complete ====="
git status --short
git log --oneline --max-count=3
echo
read -r -p "Press Enter to close..."
