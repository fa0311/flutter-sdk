#!/usr/bin/env bash
# Dispatches the "Build Dart SDK (eMudhra patched)" workflow once per version.
#
# Usage: emudhra/dispatch.sh [VERSION...]
#   With no arguments every version in emudhra/VERSIONS is dispatched.
# Environment:
#   GITHUB_TOKEN   token with permission to dispatch workflows (required)
#   REPO_SLUG      owner/repo (default: fa0311/flutter-sdk-eMudhra)
#   REF            branch holding the workflow file (default: main)
#   PUBLISH        "true" to publish the release at the end (default: true)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SLUG="${REPO_SLUG:-fa0311/flutter-sdk-eMudhra}"
REF="${REF:-main}"
PUBLISH="${PUBLISH:-true}"
WORKFLOW="build-dart-sdk.yml"
: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"

if [ $# -gt 0 ]; then
  VERSIONS="$*"
else
  VERSIONS="$(grep -v '^#' "${HERE}/VERSIONS" | grep -v '^\s*$')"
fi

for V in ${VERSIONS}; do
  printf '%s: ' "${V}"
  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${REPO_SLUG}/actions/workflows/${WORKFLOW}/dispatches" \
    -d "{\"ref\":\"${REF}\",\"inputs\":{\"version\":\"${V}\",\"publish_release\":\"${PUBLISH}\"}}")"
  if [ "${code}" = "204" ]; then
    echo "dispatched"
  else
    echo "FAILED (HTTP ${code})"
    exit 1
  fi
  sleep 1
done
echo "runs: https://github.com/${REPO_SLUG}/actions/workflows/${WORKFLOW}"
