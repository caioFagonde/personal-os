#!/usr/bin/env bash
set -Eeuo pipefail

TASK="${1:?task id required}"
BASE_REF="${2:-HEAD}"
BRANCH="agent/$TASK"

if ! git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "✗ Missing branch: $BRANCH"
  exit 2
fi

changed="$(git diff --name-only "$BASE_REF..$BRANCH" || true)"

if [[ -z "$changed" ]]; then
  echo "✗ $TASK produced no changes"
  exit 1
fi

echo "Changed files:"
echo "$changed"
echo

real_changed="$(echo "$changed" | grep -Ev '^\.agentops/(config\.json|events\.jsonl|budget\.json|runtime/|reports/)' || true)"

if [[ -z "$real_changed" ]]; then
  echo "✗ $TASK changed only AgentOps metadata/reports. Treating as failed worker."
  exit 1
fi

report_path=".agentops/reports/$TASK/report.md"
report_text=""
if git cat-file -e "$BRANCH:$report_path" 2>/dev/null; then
  report_text="$(git show "$BRANCH:$report_path")"
fi

if echo "$report_text" | grep -Eiq 'No files were changed|required report could not be written|Restart the worker|workspace-write sandbox|Status: FAILED'; then
  echo "✗ $TASK report declares failure. Treating branch as failed."
  exit 1
fi

echo "✓ $TASK produced implementation changes"
echo "$real_changed"
