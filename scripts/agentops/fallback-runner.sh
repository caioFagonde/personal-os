#!/usr/bin/env bash
set -o pipefail
set -u

TASK="${1:?task id required}"
PERMISSION="${2:-workspace}"          # workspace | full
FALLBACK_ENGINE="${3:-ask}"           # ask | codex | antigravity | retry | pause
PREVIOUS_LOG="${4:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WT="${ROOT}/.agent-worktrees/${TASK}"
PROMPT_FILE="${ROOT}/.agentops/tasks/${TASK}.prompt.md"
LOG_DIR="${ROOT}/.agentops/runtime/logs"
EVENTS="${ROOT}/.agentops/events.jsonl"
REPORT_DIR="${ROOT}/.agentops/reports/${TASK}"

mkdir -p "${LOG_DIR}" "${REPORT_DIR}" "$(dirname "${EVENTS}")"

event() {
  local type="${1:-event}"
  local msg="${2:-}"
  python3 - "${EVENTS}" "${TASK}" "${type}" "${msg}" <<'PY' 2>/dev/null || true
import json
import sys
import time

path, task, typ, msg = sys.argv[1:]
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": task,
        "type": typ,
        "message": msg,
    }) + "\n")
PY
}

ensure_worktree() {
  cd "${ROOT}" || return 1

  if [[ -d "${WT}" && ( -d "${WT}/.git" || -f "${WT}/.git" ) ]]; then
    return 0
  fi

  local branch="agent/${TASK}"

  if git show-ref --verify --quiet "refs/heads/${branch}"; then
    git worktree add "${WT}" "${branch}"
  else
    git worktree add "${WT}" -b "${branch}"
  fi
}

build_fallback_prompt() {
  local previous_log="${1:-}"
  local fallback_prompt="${WT}/.agentops/fallback-prompt.md"

  mkdir -p "${WT}/.agentops"

  {
    echo "# AgentOps fallback continuation"
    echo
    echo "Task: ${TASK}"
    echo
    echo "The previous Claude worker could not continue, likely due to usage/rate limits."
    echo "Continue from the existing worktree. Preserve scope, allowed paths, security boundaries, acceptance criteria, and report requirements."
    echo
    echo "## Original task prompt"
    echo
    echo '```markdown'
    if [[ -f "${PROMPT_FILE}" ]]; then
      cat "${PROMPT_FILE}"
    else
      echo "Missing prompt file: ${PROMPT_FILE}"
    fi
    echo
    echo '```'
    echo

    if [[ -n "${previous_log}" && -f "${previous_log}" ]]; then
      echo "## Previous worker log tail"
      echo
      echo '```text'
      tail -220 "${previous_log}" || true
      echo
      echo '```'
      echo
    fi

    echo "## Existing worktree state"
    echo
    echo '```text'
    git -C "${WT}" status --short 2>/dev/null || true
    echo
    git -C "${WT}" diff --stat 2>/dev/null || true
    echo '```'
    echo
    echo "## Required final actions"
    echo "- Continue from the existing dirty worktree."
    echo "- Keep changes bounded to this task."
    echo "- Do not read, modify, print, or commit .env, secrets, tokens, credentials, backups, logs, or private data."
    echo "- Run available checks where practical."
    echo "- Write a report to .agentops/reports/${TASK}/report.md."
    echo "- Do not push."
  } > "${fallback_prompt}"

  echo "${fallback_prompt}"
}

commit_if_dirty() {
  cd "${WT}" || return 1

  mkdir -p ".agentops/reports/${TASK}"

  if [[ ! -f ".agentops/reports/${TASK}/report.md" ]]; then
    {
      echo "# ${TASK} report"
      echo
      echo "Status: COMPLETED_BY_FALLBACK"
      echo
      echo "Fallback engine completed but did not write a structured report."
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
    } > ".agentops/reports/${TASK}/report.md"
  fi

  if git status --short | grep -q .; then
    git add .
    git commit -m "Agent fallback task: ${TASK}" || true
  fi

  mkdir -p "${ROOT}/.agentops/reports/${TASK}"
  cp -f ".agentops/reports/${TASK}/report.md" "${ROOT}/.agentops/reports/${TASK}/report.md" 2>/dev/null || true
}

run_codex_fallback() {
  local previous_log="${1:-}"

  ensure_worktree || return 1

  local fallback_prompt
  fallback_prompt="$(build_fallback_prompt "${previous_log}")"

  local log_file="${LOG_DIR}/${TASK}-codex-fallback-$(date +%Y%m%d-%H%M%S).log"
  event "fallback_started" "codex fallback started"

  echo
  echo "Continuing ${TASK} with Codex/GPT..."
  echo "Worktree: ${WT}"
  echo "Prompt:   ${fallback_prompt}"
  echo "Log:      ${log_file}"
  echo

  local rc=0

  if [[ "${PERMISSION}" == "full" ]]; then
    codex exec \
      --dangerously-bypass-approvals-and-sandbox \
      --cd "${WT}" \
      "$(cat "${fallback_prompt}")" 2>&1 | tee "${log_file}"
    rc="${PIPESTATUS[0]}"
  else
    codex exec \
      --sandbox workspace-write \
      --cd "${WT}" \
      "$(cat "${fallback_prompt}")" 2>&1 | tee "${log_file}"
    rc="${PIPESTATUS[0]}"
  fi

  if [[ "${rc}" -eq 0 ]]; then
    event "fallback_completed" "codex fallback completed"
    commit_if_dirty || true
  else
    event "fallback_failed" "codex fallback exited with code ${rc}"
  fi

  return "${rc}"
}

run_antigravity_fallback() {
  local previous_log="${1:-}"

  ensure_worktree || return 1

  local fallback_prompt
  fallback_prompt="$(build_fallback_prompt "${previous_log}")"

  local log_file="${LOG_DIR}/${TASK}-antigravity-fallback-$(date +%Y%m%d-%H%M%S).log"
  event "fallback_started" "antigravity fallback started"

  echo
  echo "Continuing ${TASK} with Antigravity..."
  echo "Worktree: ${WT}"
  echo "Prompt:   ${fallback_prompt}"
  echo "Log:      ${log_file}"
  echo

  cd "${WT}" || return 1

  if [[ -n "${AGENTOPS_ANTIGRAVITY_EXEC_TEMPLATE:-}" ]]; then
    local cmd="${AGENTOPS_ANTIGRAVITY_EXEC_TEMPLATE//\{prompt\}/${fallback_prompt}}"
    cmd="${cmd//\{worktree\}/${WT}}"

    bash -lc "${cmd}" 2>&1 | tee "${log_file}"
    local rc="${PIPESTATUS[0]}"

    if [[ "${rc}" -eq 0 ]]; then
      event "fallback_completed" "antigravity fallback completed"
      commit_if_dirty || true
    else
      event "fallback_failed" "antigravity fallback exited with code ${rc}"
    fi

    return "${rc}"
  fi

  if command -v agy >/dev/null 2>&1; then
    {
      echo "Starting interactive Antigravity in ${WT}"
      echo
      echo "Execute this prompt:"
      echo "${fallback_prompt}"
      echo
    } | tee "${log_file}"

    agy 2>&1 | tee -a "${log_file}"
    local rc="${PIPESTATUS[0]}"

    if [[ "${rc}" -eq 0 ]]; then
      event "fallback_completed" "antigravity interactive session completed"
      commit_if_dirty || true
    else
      event "fallback_failed" "antigravity exited with code ${rc}"
    fi

    return "${rc}"
  fi

  echo "Antigravity CLI 'agy' not found." | tee "${log_file}"
  event "fallback_failed" "agy not found"
  return 127
}

ask_fallback() {
  local previous_log="${1:-}"

  echo
  echo "Claude appears unavailable for this task."
  echo
  echo "Choose continuation:"
  echo "  1) Continue with Codex/GPT"
  echo "  2) Continue with Antigravity"
  echo "  3) Retry Claude later"
  echo "  4) Pause and leave worktree untouched"
  echo

  local choice
  read -r -p "Selection [1-4]: " choice

  case "${choice}" in
    1) run_codex_fallback "${previous_log}" ;;
    2) run_antigravity_fallback "${previous_log}" ;;
    3) return 75 ;;
    4|"") return 76 ;;
    *) echo "Invalid selection."; return 2 ;;
  esac
}

case "${FALLBACK_ENGINE}" in
  ask) ask_fallback "${PREVIOUS_LOG}" ;;
  codex|gpt) run_codex_fallback "${PREVIOUS_LOG}" ;;
  antigravity|agy) run_antigravity_fallback "${PREVIOUS_LOG}" ;;
  retry) exit 75 ;;
  pause|none) exit 76 ;;
  *) echo "Unknown fallback engine: ${FALLBACK_ENGINE}"; exit 2 ;;
esac
