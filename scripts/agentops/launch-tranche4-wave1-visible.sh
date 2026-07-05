#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

MODE="${AGENTOPS_MODE:-headless}"
PERMISSION="${AGENTOPS_PERMISSION:-workspace}"
TERMINAL="${AGENTOPS_TERMINAL:-auto}"

TASKS=(
  nexus-ui-design-system
  mobile-offline-sync-continuity
  tailscale-ntfy-pairing
)

launch() {
  local task="$1"
  local title="agent:$task"
  local cmd="cd '$ROOT' && exec scripts/agentops/run-visible-task.sh '$task' '$MODE' '$PERMISSION'"

  echo "Launching $task"

  if [[ "$TERMINAL" == "tmux" ]]; then
    tmux new-session -d -s agentops 2>/dev/null || true
    tmux new-window -t agentops -n "$task" "bash -lc '$cmd'"
    return
  fi

  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -lc "$cmd"
  elif command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -T "$title" -e bash -lc "$cmd"
  elif command -v kgx >/dev/null 2>&1; then
    kgx --title="$title" -- bash -lc "$cmd"
  elif command -v konsole >/dev/null 2>&1; then
    konsole --new-tab --title "$title" -e bash -lc "$cmd"
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$title" --command="bash -lc '$cmd'"
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$cmd" &
  elif command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s agentops 2>/dev/null || true
    tmux new-window -t agentops -n "$task" "bash -lc '$cmd'"
    echo "No GUI terminal found. Attach with: tmux attach -t agentops"
  else
    echo "No terminal emulator found. Run manually:"
    echo "$cmd"
  fi
}

echo "Checking task visibility before launch..."
for task in "${TASKS[@]}"; do
  agentops list | grep -q "$task" || {
    echo "Missing task in current repo: $task"
    exit 1
  }
done

echo "Launching visible AgentOps Wave 1..."
for task in "${TASKS[@]}"; do
  launch "$task"
done

echo
echo "Launched."
echo "Monitor:"
echo "  agentops tui"
echo "  tail -f .agentops/events.jsonl"
echo "  tail -f .agentops/runtime/logs/*.log"
