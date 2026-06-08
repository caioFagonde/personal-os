#!/usr/bin/env bash
set -Eeuo pipefail
while true; do
  clear
  date
  python3 scripts/agents/agentctl.py status
  echo
  echo "Reports: .agents/reports/<task-id>/report.md"
  sleep "${AGENTOPS_MONITOR_INTERVAL:-10}"
done
