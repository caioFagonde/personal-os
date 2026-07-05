#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
: "${GITHUB_RELEASE_REPO:=}"
: "${GITHUB_RELEASE_TOKEN:=}"
: "${GITHUB_RELEASE_TAG:=}"
: "${PUBLISH_RELEASE_DRY_RUN:=true}"
if [[ -z "$GITHUB_RELEASE_TAG" ]]; then
  GITHUB_RELEASE_TAG="v$(python3 scripts/release/build-manifest.py --print-version 2>/dev/null || date +%Y.%m.%d.%H%M)"
fi
mkdir -p dist/release
python3 scripts/release/build-manifest.py > dist/release/release-manifest.json
./scripts/release/verify-release-artifacts.sh || true
if [[ "$PUBLISH_RELEASE_DRY_RUN" == "true" ]]; then
  echo "Dry-run release publication for $GITHUB_RELEASE_TAG"
  echo "Set PUBLISH_RELEASE_DRY_RUN=false, GITHUB_RELEASE_REPO, and GITHUB_RELEASE_TOKEN to publish."
  exit 0
fi
[[ -n "$GITHUB_RELEASE_REPO" && -n "$GITHUB_RELEASE_TOKEN" ]] || { echo "GITHUB_RELEASE_REPO and GITHUB_RELEASE_TOKEN are required" >&2; exit 2; }
python3 scripts/release/publish_github_release.py --repo "$GITHUB_RELEASE_REPO" --token "$GITHUB_RELEASE_TOKEN" --tag "$GITHUB_RELEASE_TAG" --manifest dist/release/release-manifest.json
