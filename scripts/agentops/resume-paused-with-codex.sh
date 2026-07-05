#!/usr/bin/env bash
set -Eeuo pipefail

TASK="${1:?task id required}"
MODE="${2:-workspace}" # workspace | full

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

WT="$ROOT/.agent-worktrees/$TASK"
PROMPT="$ROOT/.agentops/tasks/$TASK.prompt.md"
LOG_DIR="$ROOT/.agentops/runtime/logs"
REPORT_ROOT="$ROOT/.agentops/reports/$TASK"

if [[ ! -d "$WT" ]]; then
  echo "✗ Worktree not found: $WT"
  exit 1
fi

if [[ ! -f "$PROMPT" ]]; then
  echo "✗ Prompt not found: $PROMPT"
  exit 1
fi

mkdir -p "$LOG_DIR" "$REPORT_ROOT" "$WT/.agentops/reports/$TASK"

LATEST_LOG="$(ls -t "$LOG_DIR/$TASK-"*.log 2>/dev/null | head -1 || true)"
RESUME_PROMPT="$WT/.agentops/codex-resume-$TASK.md"
CODEX_LOG="$LOG_DIR/$TASK-codex-resume-$(date +%Y%m%d-%H%M%S).log"

{
  echo "# Codex continuation for AgentOps task: $TASK"
  echo
  echo "You are resuming a paused AgentOps worker."
  echo
  echo "Claude hit a session/usage limit. Continue from the existing git worktree."
  echo
  echo "## Required behavior"
  echo
  echo "- Continue from the current worktree state."
  echo "- Preserve the original task scope and acceptance criteria."
  echo "- Keep changes bounded to the task."
  echo "- Do not read, modify, print, or commit .env files, secrets, tokens, credentials, backups, private data, or runtime logs."
  echo "- Run relevant checks where practical."
  echo "- Write a report to .agentops/reports/$TASK/report.md."
  echo "- Do not push."
  echo
  echo "## Original task prompt"
  echo
  echo '```markdown'
  cat "$PROMPT"
  echo
  echo '```'
  echo
  echo "## Current worktree status"
  echo
  echo '```text'
  git -C "$WT" status --short || true
  echo
  git -C "$WT" diff --stat || true
  echo '```'
  echo
  if [[ -n "$LATEST_LOG" && -f "$LATEST_LOG" ]]; then
    echo "## Previous worker log tail"
    echo
    echo '```text'
    tail -220 "$LATEST_LOG" || true
    echo
    echo '```'
  fi
  echo
  echo "## Final report format"
  echo
  echo "Write .agentops/reports/$TASK/report.md with:"
  echo "- Status"
  echo "- Summary"
  echo "- Files changed"
  echo "- Tests run"
  echo "- Known issues"
  echo "- Merge notes"
} > "$RESUME_PROMPT"

echo "Resuming $TASK with Codex"
echo "Worktree: $WT"
echo "Prompt:   $RESUME_PROMPT"
echo "Log:      $CODEX_LOG"
echo

if [[ "$MODE" == "full" ]]; then
  codex exec \
    --dangerously-bypass-approvals-and-sandbox \
    --cd "$WT" \
    "$(cat "$RESUME_PROMPT")" 2>&1 | tee "$CODEX_LOG"
else
  codex exec \
    --sandbox workspace-write \
    --cd "$WT" \
    "$(cat "$RESUME_PROMPT")" 2>&1 | tee "$CODEX_LOG"
fi

RC="${PIPESTATUS[0]}"

if [[ "$RC" -ne 0 ]]; then
  echo "✗ Codex exited with code $RC"
  exit "$RC"
fi

cd "$WT"

if [[ ! -f ".agentops/reports/$TASK/report.md" ]]; then
  {
    echo "# $TASK report"
    echo
    echo "Status: COMPLETED_BY_CODEX_RESUME"
    echo
    echo "Codex completed but did not write a structured report."
    echo
    echo "## Git status"
    echo
    echo '```text'
    git status --short || true
    echo '```'
    echo
    echo "## Diff stat"
    echo
    echo '```text'
    git diff --stat || true
    echo '```'
  } > ".agentops/reports/$TASK/report.md"
fi

if git status --short | grep -q .; then
  git add .
  git commit -m "Agent task: $TASK resumed with Codex" || true
else
  echo "No changes to commit for $TASK"
fi

mkdir -p "$REPORT_ROOT"
cp -f ".agentops/reports/$TASK/report.md" "$REPORT_ROOT/report.md" 2>/dev/null || true

echo
echo "✓ Resume complete for $TASK"
git status --short
git log --oneline --max-count=3
