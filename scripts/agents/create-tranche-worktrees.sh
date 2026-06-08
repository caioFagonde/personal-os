#!/usr/bin/env bash
set -Eeuo pipefail
for task in "$@"; do
  python3 scripts/agents/agentctl.py create-worktree "$task"
done
