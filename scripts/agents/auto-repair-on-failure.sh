#!/usr/bin/env bash
set -Eeuo pipefail

LABEL="${1:-qa-checks}"
FAILED_COMMAND="${2:-unknown command}"
LOG_FILE="${3:-}"
MAX_REPAIR_ATTEMPTS="${AGENTOPS_REPAIR_ATTEMPTS:-2}"
REPAIR_MODEL="${CLAUDE_REPAIR_MODEL:-sonnet}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

mkdir -p .agents/reports/auto-repair .agents/tasks

timestamp="$(date +%Y%m%d-%H%M%S)"
task="auto-repair-${LABEL}-${timestamp}"
branch="agent/${task}"
wt="$ROOT/.agent-worktrees/${task}"
prompt_file="$ROOT/.agents/tasks/${task}.prompt.md"
report_dir="$ROOT/.agents/reports/${task}"

mkdir -p "$report_dir"

if [[ -z "$LOG_FILE" || ! -f "$LOG_FILE" ]]; then
  LOG_FILE="$report_dir/failure.log"
  echo "No failure log was provided." > "$LOG_FILE"
fi

echo "===== Auto repair requested ====="
echo "Label:          $LABEL"
echo "Failed command: $FAILED_COMMAND"
echo "Failure log:    $LOG_FILE"
echo "Task:           $task"
echo "Branch:         $branch"
echo "Worktree:       $wt"
echo "Model:          $REPAIR_MODEL"
echo

git worktree remove --force "$wt" 2>/dev/null || true
rm -rf "$wt"
git branch -D "$branch" 2>/dev/null || true

git worktree add "$wt" -b "$branch"

cat > "$prompt_file" <<EOF
You are the automatic QA repair node for Personal OS.

You are running inside an isolated git worktree.

Task:
Fix the concrete test/check failure below. Do not add broad new features. Do not perform unrelated refactors. Make the smallest correct change that satisfies the failing tests and preserves product intent.

Hard security rules:
- Do not read, print, modify, or commit .env, .env.*, secrets/, data/, backups/, logs/, credentials, tokens, OAuth secrets, private keys, or personal data.
- Do not weaken auth/security.
- Do not add arbitrary remote shell.
- Do not run destructive commands.
- Do not commit or push to remote.
- Do not hide test failures by deleting meaningful tests.
- If a test is wrong, update it only with a precise justification and maintain the intended invariant.

Failed command:
\`\`\`bash
$FAILED_COMMAND
\`\`\`

Failure output:
\`\`\`text
$(sed -e 's/`/\\`/g' "$LOG_FILE" | tail -300)
\`\`\`

Current known failure examples may include:
- missing structured error constant such as optional_service_unavailable
- page missing expected visual class such as glass-card
- Settings page missing validation rules
- Settings page missing localStorage persistence contract
- Settings page missing serviceStatus/checkServices contract

Repair requirements:
1. Inspect only relevant files.
2. Fix the actual root cause.
3. Add or preserve tests.
4. Run the failing command again if possible.
5. Run:
   - python3 -m pytest tests -q
   - ./scripts/check-secrets.sh
6. Write a report to:
   .agents/reports/$task/report.md

Report must include:
- root cause
- files changed
- tests run
- results
- remaining risks
EOF

cd "$wt"

mkdir -p ".agents/reports/$task"

run_claude_repair() {
  local prompt_text
  prompt_text="$(cat "$prompt_file")"

  local model_args=()
  if claude --help 2>&1 | grep -q -- '--model'; then
    model_args=(--model "$REPAIR_MODEL")
  fi

  if claude --help 2>&1 | grep -q -- '--permission-mode'; then
    claude "${model_args[@]}" --permission-mode bypassPermissions -p "$prompt_text"
  else
    claude "${model_args[@]}" --dangerously-skip-permissions -p "$prompt_text"
  fi
}

RC=0
run_claude_repair || RC=$?

if [[ "$RC" -ne 0 ]]; then
  {
    echo "# $task report"
    echo
    echo "Status: FAILED"
    echo
    echo "Claude repair node exited with code $RC."
    echo
    echo "## Failure command"
    echo
    echo '```bash'
    echo "$FAILED_COMMAND"
    echo '```'
    echo
    echo "## Git status"
    git status --short || true
    echo
    echo "## Diff stat"
    git diff --stat || true
  } > ".agents/reports/$task/report.md"

  echo "Auto repair node failed."
  cat ".agents/reports/$task/report.md"
  exit "$RC"
fi

if [[ ! -f ".agents/reports/$task/report.md" ]]; then
  {
    echo "# $task report"
    echo
    echo "Status: COMPLETED_WITHOUT_EXPLICIT_REPORT"
    echo
    echo "Claude completed but did not write a structured report."
    echo
    echo "## Git status"
    git status --short || true
    echo
    echo "## Diff stat"
    git diff --stat || true
  } > ".agents/reports/$task/report.md"
fi

if git status --short | grep -q .; then
  git add .
  git commit -m "Agent repair: $LABEL"
else
  echo "Repair node produced no changes."
fi

cd "$ROOT"

mkdir -p ".agents/reports/$task"
cp -f "$wt/.agents/reports/$task/report.md" ".agents/reports/$task/report.md" 2>/dev/null || true

echo
echo "===== Auto repair branch ready ====="
echo "Branch: $branch"
git diff --stat "HEAD..$branch" || true
