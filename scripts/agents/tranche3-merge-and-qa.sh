#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

IMPLEMENTERS=("intelligence-layer" "connector-marketplace" "obsidian-notion-trello")
QA_TASK="qa-route-endpoint-repair"

run_checks_raw() {
  echo
  echo "===== Running checks ====="
  python3 -m pytest tests -q
  ./scripts/check-secrets.sh
  bash -n scripts/*.sh scripts/agents/*.sh scripts/certify/*.sh 2>/dev/null || true
  docker compose --env-file .env --profile full config >/tmp/personal-os-full.yml

  if command -v pnpm >/dev/null 2>&1; then
    if [[ ! -d node_modules && ! -d apps/web/node_modules ]]; then
      echo "Installing pnpm dependencies..."
      corepack enable || true
      corepack prepare pnpm@9.12.0 --activate || true
      pnpm install --no-frozen-lockfile
    fi
    pnpm --dir apps/web build
  else
    echo "pnpm not found; skipping web build"
  fi
}

run_checks() {
  local label="${1:-checks}"
  local max_attempts="${AGENTOPS_REPAIR_ATTEMPTS:-2}"
  local attempt=0
  local log_dir="$ROOT/.agents/reports/auto-repair"
  mkdir -p "$log_dir"

  while true; do
    local log_file="$log_dir/${label}-attempt-${attempt}.log"

    echo
    echo "===== Running checks for $label, attempt $attempt ====="

    if run_checks_raw 2>&1 | tee "$log_file"; then
      echo "Checks passed for $label"
      return 0
    fi

    echo
    echo "Checks failed for $label. Log: $log_file"

    if [[ "$attempt" -ge "$max_attempts" ]]; then
      echo "Repair attempt limit reached for $label."
      return 1
    fi

    attempt=$((attempt + 1))

    echo
    echo "===== Spawning Sonnet repair node for $label ====="
    scripts/agents/auto-repair-on-failure.sh "$label" "run_checks_raw" "$log_file"

    local repair_branch
    repair_branch="$(git branch --list 'agent/auto-repair-*' --sort=-committerdate | head -1 | sed 's/^..//')"

    if [[ -z "$repair_branch" ]]; then
      echo "Could not locate auto-repair branch."
      return 1
    fi

    echo "Merging repair branch: $repair_branch"

    if git diff --quiet "HEAD..$repair_branch"; then
      echo "Repair branch has no changes. Cannot continue automatically."
      return 1
    fi

    git merge --no-ff "$repair_branch" -m "Merge auto repair for $label"

    echo
    echo "Repair branch merged. Re-running checks..."
  done
}

commit_dirty_worktree() {
  local task="$1"
  local wt="$ROOT/.agent-worktrees/$task"

  if [[ ! -d "$wt" ]]; then
    echo "Missing worktree: $task"
    return 0
  fi

  if git -C "$wt" status --short | grep -q .; then
    echo "Committing dirty worktree: $task"
    git -C "$wt" add .
    git -C "$wt" commit -m "Agent task: $task" || true
  else
    echo "Clean worktree: $task"
  fi
}

merge_task() {
  local task="$1"
  local branch="agent/$task"
  local current
  current="$(git branch --show-current)"

  echo
  echo "===== Merge candidate: $task ====="

  if ! git show-ref --verify --quiet "refs/heads/$branch"; then
    echo "Branch missing: $branch; skipping"
    return 0
  fi

  if git diff --quiet "$current..$branch"; then
    echo "No changes to merge for $task"
    return 0
  fi

  echo "Merging $branch..."
  git merge --no-ff "$branch" -m "Merge agent task: $task"
  run_checks "$task"
}

run_agent_headless() {
  local task="$1"
  local engine="$2"
  local wt="$ROOT/.agent-worktrees/$task"
  local prompt="$ROOT/.agents/tasks/$task.prompt.md"

  cd "$wt"
  mkdir -p ".agents/reports/$task"

  local rc=0
  local prompt_text
  prompt_text="$(cat "$prompt")"

  if [[ "$engine" == "claude" ]]; then
    if claude --help 2>&1 | grep -q -- '--permission-mode'; then
      claude --permission-mode bypassPermissions -p "$prompt_text" || rc=$?
    else
      claude --dangerously-skip-permissions -p "$prompt_text" || rc=$?
    fi
  else
    # codex-cli 0.137.0 does not support --ask-for-approval.
    # Use the isolated worktree as the containment boundary.
    codex exec \
      --dangerously-bypass-approvals-and-sandbox \
      --cd "$wt" \
      "$prompt_text" || rc=$?
  fi

  if [[ "$rc" -ne 0 ]]; then
    {
      echo "# $task report"
      echo
      echo "Status: FAILED"
      echo
      echo "Agent exited with code $rc."
      echo
      echo "## Git status"
      git status --short || true
      echo
      echo "## Diff stat"
      git diff --stat || true
    } > ".agents/reports/$task/report.md"

    cd "$ROOT"
    return "$rc"
  fi

  if [[ ! -f ".agents/reports/$task/report.md" ]]; then
    {
      echo "# $task report"
      echo
      echo "Status: COMPLETED_WITHOUT_EXPLICIT_REPORT"
      echo
      echo "Auto-generated placeholder after successful headless run."
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
    git commit -m "Agent task: $task"
  fi

  cd "$ROOT"
}

echo "Collecting reports before merge..."
python3 scripts/agents/agentctl.py collect || true

echo
echo "===== Pre-merge checks ====="
run_checks "pre-merge"

echo
echo "===== Commit dirty implementer worktrees ====="
for task in "${IMPLEMENTERS[@]}"; do
  commit_dirty_worktree "$task"
done

echo
echo "===== Merge implementers sequentially ====="
for task in "${IMPLEMENTERS[@]}"; do
  merge_task "$task"
done

echo
echo "===== Create QA worktree from integrated branch ====="
python3 scripts/agents/agentctl.py create-worktree "$QA_TASK" || true

echo
echo "===== Run QA and repair node ====="
run_agent_headless "$QA_TASK" claude

echo
echo "===== Merge QA and repair node ====="
merge_task "$QA_TASK"

echo
echo "===== Final tranche 3 checks ====="
python3 scripts/agents/agentctl.py collect || true
cat .agents/reports/TRANCHE_REPORT.md || true
run_checks "final-tranche-3"

echo
echo "Tranche 3 integration complete."
echo "Recommended next manual checks:"
echo "  ./scripts/bootstrap.sh --full --open"
echo "  docker compose --env-file .env ps"
echo "  open http://localhost:9000"
