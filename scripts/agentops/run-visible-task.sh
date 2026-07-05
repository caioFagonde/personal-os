#!/usr/bin/env bash
set -uo pipefail

TASK="${1:?task id required}"
MODE="${2:-headless}"
PERMISSION="${3:-workspace}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

LOG_DIR=".agentops/runtime/logs"
EVENTS=".agentops/events.jsonl"
mkdir -p "$LOG_DIR" ".agentops/runtime" ".agentops/reports"

LOG_FILE="$LOG_DIR/${TASK}-$(date +%Y%m%d-%H%M%S).log"

json_event() {
  local type="$1"
  local msg="$2"
  python3 - "$EVENTS" "$TASK" "$type" "$msg" <<'PY' 2>/dev/null || true
import json, sys, time
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

looks_like_usage_limit() {
  local file="$1"
  grep -Eiq \
    'usage limit|rate limit|too many requests|429|quota|limit reached|try again|reset|5.?hour|five.?hour|claude.*limit|overloaded|temporarily unavailable' \
    "$file"
}

frames=(
  "◐ calibrating worker lattice"
  "◓ reading task context"
  "◑ mapping worktree"
  "◒ synthesizing patch plan"
  "◆ executing bounded changes"
  "◇ watching reports"
  "✦ checking invariants"
  "✧ preserving security boundaries"
)

banner() {
  printf '\033[2J\033[H'
  cat <<EOF
╔════════════════════════════════════════════════════════════════════╗
║                         AGENTOPS SWARM                            ║
╠════════════════════════════════════════════════════════════════════╣
║ Task:       $TASK
║ Mode:       $MODE
║ Permission: $PERMISSION
║ Repo:       $ROOT
║ Log:        $LOG_FILE
╚════════════════════════════════════════════════════════════════════╝

EOF
}

banner
json_event "started" "visible runner started"

if ! agentops list | grep -q "$TASK"; then
  echo "Unknown task in main repo: $TASK" | tee -a "$LOG_FILE"
  json_event "failed" "unknown task in main repo"
  exit 2
fi

AGENTOPS_PYTHON="${AGENTOPS_PYTHON:-/usr/bin/python3}" \
agentops run "$TASK" --mode "$MODE" --permission "$PERMISSION" >"$LOG_FILE" 2>&1 &
PID=$!

json_event "process_started" "worker pid $PID"

start_ts="$(date +%s)"
i=0

while kill -0 "$PID" 2>/dev/null; do
  now="$(date +%s)"
  elapsed=$((now - start_ts))
  frame="${frames[$((i % ${#frames[@]}))]}"

  banner
  printf "Status:      running\n"
  printf "Elapsed:     %02d:%02d\n" "$((elapsed / 60))" "$((elapsed % 60))"
  printf "Animation:   %s\n" "$frame"
  printf "PID:         %s\n\n" "$PID"

  printf "Latest output:\n"
  printf "────────────────────────────────────────────────────────────────────\n"
  tail -n 26 "$LOG_FILE" 2>/dev/null || true
  printf "\n────────────────────────────────────────────────────────────────────\n"

  i=$((i + 1))
  sleep 2
done

wait "$PID"
RC=$?

banner

if [[ "$RC" -eq 0 ]]; then
  json_event "completed" "worker completed successfully"
  echo "Status: completed"
else
  json_event "failed" "worker exited with code $RC"
  echo "Status: failed with code $RC"
fi

echo
echo "Final output:"
echo "────────────────────────────────────────────────────────────────────"
tail -n 120 "$LOG_FILE" 2>/dev/null || true
echo "────────────────────────────────────────────────────────────────────"
echo

if [[ "$RC" -ne 0 ]]; then
  SHOULD_FALLBACK=false

  if looks_like_usage_limit "$LOG_FILE"; then
    SHOULD_FALLBACK=true
    echo "Detected likely Claude usage/rate-limit condition."
  elif [[ "${AGENTOPS_FALLBACK_ON_ANY_FAILURE:-false}" == "true" ]]; then
    SHOULD_FALLBACK=true
    echo "Worker failed and AGENTOPS_FALLBACK_ON_ANY_FAILURE=true."
  fi

  if [[ "$SHOULD_FALLBACK" == "true" ]]; then
    FALLBACK="${AGENTOPS_FALLBACK:-ask}"
    echo
    echo "Fallback mode: $FALLBACK"
    echo

    scripts/agentops/fallback-runner.sh "$TASK" "$PERMISSION" "$FALLBACK" "$LOG_FILE"
    FALLBACK_RC=$?

    echo
    echo "Fallback exited with code: $FALLBACK_RC"

    if [[ "$FALLBACK_RC" -eq 0 ]]; then
      RC=0
    elif [[ "$FALLBACK_RC" -eq 75 ]]; then
      echo "Retry requested. Leave this task paused and rerun later."
    elif [[ "$FALLBACK_RC" -eq 76 ]]; then
      echo "Task paused. Worktree preserved."
    fi
  else
    echo "No fallback triggered. Set AGENTOPS_FALLBACK_ON_ANY_FAILURE=true to ask on any failure."
  fi
fi

echo
echo "Worktree status:"
git -C ".agent-worktrees/$TASK" status --short 2>/dev/null || true

echo
echo "Reports:"
find ".agent-worktrees/$TASK" -path "*/report.md" -print 2>/dev/null || true

echo
read -r -p "Press Enter to close..."
exit "$RC"
