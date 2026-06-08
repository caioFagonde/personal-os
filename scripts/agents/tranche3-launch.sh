#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

MODE="${AGENTOPS_MODE:-headless}"           # headless | interactive
PERMISSION="${AGENTOPS_PERMISSION:-full}"   # workspace | full
TERMINAL="${AGENTOPS_TERMINAL:-auto}"       # auto | gnome | xterm | tmux | current

TASKS=("intelligence-layer" "connector-marketplace" "obsidian-notion-trello")

task_engine() {
  case "$1" in
    intelligence-layer) echo "claude" ;;
    connector-marketplace) echo "claude" ;;
    obsidian-notion-trello) echo "codex" ;;
    *) echo "claude" ;;
  esac
}

launch_terminal() {
  local title="$1"
  local command="$2"

  echo "Launching: $title"
  echo "Command: $command"
  echo

  case "$TERMINAL" in
    current)
      bash -lc "$command"
      return
      ;;
    tmux)
      command -v tmux >/dev/null 2>&1 || {
        echo "tmux not found"
        return 1
      }
      tmux new-session -d -s tranche3 2>/dev/null || true
      tmux new-window -t tranche3 -n "$title" "bash -lc '$command'"
      return
      ;;
    gnome)
      command -v gnome-terminal >/dev/null 2>&1 || {
        echo "gnome-terminal not found"
        return 1
      }
      gnome-terminal --title="$title" -- bash -lc "$command"
      return
      ;;
  esac

  # auto mode
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -lc "$command" && return
  fi

  if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -T "$title" -e bash -lc "$command" && return
  fi

  if command -v kgx >/dev/null 2>&1; then
    kgx --title="$title" -- bash -lc "$command" && return
  fi

  if command -v konsole >/dev/null 2>&1; then
    konsole --new-tab --title "$title" -e bash -lc "$command" && return
  fi

  if command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$title" --command="bash -lc '$command'" && return
  fi

  if command -v kitty >/dev/null 2>&1; then
    kitty --title "$title" bash -lc "$command" && return
  fi

  if command -v alacritty >/dev/null 2>&1; then
    alacritty --title "$title" -e bash -lc "$command" && return
  fi

  if command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -lc "$command" &
    return
  fi

  if command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s tranche3 2>/dev/null || true
    tmux new-window -t tranche3 -n "$title" "bash -lc '$command'"
    echo "No GUI terminal found. Started tmux session."
    echo "Attach with: tmux attach -t tranche3"
    return
  fi

  echo "No supported terminal emulator found."
  echo "Run manually:"
  echo "$command"
}

echo "AgentOps tranche 3 launcher"
echo "Root:       $ROOT"
echo "Mode:       $MODE"
echo "Permission: $PERMISSION"
echo "Terminal:   $TERMINAL"
echo

echo "Desktop/session diagnostics:"
echo "DISPLAY=${DISPLAY:-}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
echo "XDG_CURRENT_DESKTOP=${XDG_CURRENT_DESKTOP:-}"
echo

echo "Available terminal emulators:"
for t in gnome-terminal x-terminal-emulator kgx konsole xfce4-terminal kitty alacritty xterm tmux; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "  found: $t -> $(command -v "$t")"
  fi
done
echo

echo "Creating tranche 3 worktrees..."
for task in "${TASKS[@]}"; do
  python3 scripts/agents/agentctl.py create-worktree "$task" || true
done

echo
echo "Launching workers..."
for task in "${TASKS[@]}"; do
  engine="$(task_engine "$task")"
  cmd="cd '$ROOT' && exec scripts/agents/run-agent-task.sh '$task' '$engine' '$MODE' '$PERMISSION'"
  launch_terminal "agent:$task" "$cmd"
done

echo
echo "Launching monitor..."
monitor_cmd="cd '$ROOT' && scripts/agents/monitor.sh; read -r -p 'Press Enter to close...'"
launch_terminal "agent:monitor" "$monitor_cmd" || true

echo
echo "Tranche 3 launch attempted."
echo
echo "If no GUI windows appeared, run:"
echo "  AGENTOPS_TERMINAL=tmux scripts/agents/tranche3-launch.sh"
echo "  tmux attach -t tranche3"
echo
echo "When workers finish, run:"
echo "  scripts/agents/tranche3-merge-and-qa.sh"
