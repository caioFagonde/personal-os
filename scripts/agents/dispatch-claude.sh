#!/usr/bin/env bash
set -Eeuo pipefail
TASK_ID="${1:?usage: scripts/agents/dispatch-claude.sh <task-id> [interactive|headless]}"
MODE="${2:-interactive}"
python3 scripts/agents/agentctl.py dispatch "$TASK_ID" --engine claude --mode "$MODE"
