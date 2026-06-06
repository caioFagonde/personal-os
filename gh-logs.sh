#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# 1. Verification of Dependencies
if ! command -v git &> /dev/null; then
    echo "Error: 'git' CLI utility is not installed or not in PATH." >&2
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: 'gh' (GitHub CLI) utility is not installed or not in PATH." >&2
    exit 1
fi

# 2. Verification of Git Context
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo "Error: The current directory is not a Git repository." >&2
    exit 1
fi

# 3. Verification of GitHub CLI Authentication
if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated. Run 'gh auth login' first." >&2
    exit 1
fi

# 4. Core Variables
OUTPUT_FILE="latest_commit_logs.txt"
COMMIT_SHA=$(git rev-parse HEAD)

echo "Target Commit SHA: $COMMIT_SHA"
echo "Querying GitHub API for matching workflow runs..."

# 5. Extract Run IDs into a Bash Array
# Uses explicit JSON parsing via jq syntax embedded in the gh CLI
mapfile -t RUN_IDS < <(gh run list --commit "$COMMIT_SHA" --json databaseId --jq '.[].databaseId' 2>/dev/null)

if [ ${#RUN_IDS[@]} -eq 0 ]; then
    echo "No GitHub Action runs found associated with commit $COMMIT_SHA."
    exit 0
fi

# 6. Stream Optimization and Output Initialization
> "$OUTPUT_FILE"

echo "Found ${#RUN_IDS[@]} workflow run(s). Extracting logs to $OUTPUT_FILE..."

# Iterate through the compiled array of database identifiers
for RUN_ID in "${RUN_IDS[@]}"; do
    {
        echo "========================================================================"
        echo "LOGS FOR WORKFLOW RUN ID: $RUN_ID"
        echo "TIMESTAMP: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        echo "========================================================================"
    } >> "$OUTPUT_FILE"

    # Download raw logs and redirect standard error to standard output streams
    gh run view "$RUN_ID" --log >> "$OUTPUT_FILE" 2>&1
    
    # Inject spacing between discrete workflow payloads
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

echo "Operation complete. Matrix logs aggregated successfully in: $(pwd)/$OUTPUT_FILE"