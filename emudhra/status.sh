#!/usr/bin/env bash
# Prints the latest workflow run (and its jobs) for every version.
#
# Usage: emudhra/status.sh [VERSION...]
# Environment: GITHUB_TOKEN (required), REPO_SLUG (default fa0311/flutter-sdk-eMudhra)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SLUG="${REPO_SLUG:-fa0311/flutter-sdk-eMudhra}"
WORKFLOW="build-dart-sdk.yml"
: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"

if [ $# -gt 0 ]; then
  VERSIONS="$*"
else
  VERSIONS="$(grep -v '^#' "${HERE}/VERSIONS" | grep -v '^\s*$')"
fi

api() {
  curl -sS -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" "https://api.github.com/$1"
}

# run-name is "Dart SDK <version> (eMudhra patched)"; newest runs first.
RUNS="$(api "repos/${REPO_SLUG}/actions/workflows/${WORKFLOW}/runs?per_page=100")"
for V in ${VERSIONS}; do
  RUN="$(printf '%s' "${RUNS}" | python3 -c '
import sys, json
v = sys.argv[1]
for r in json.load(sys.stdin).get("workflow_runs", []):
    if r.get("display_title") == f"Dart SDK {v} (eMudhra patched)":
        print(r["id"], r["status"], r["conclusion"] or "-", r["html_url"]); break
' "${V}")"
  if [ -z "${RUN}" ]; then
    echo "${V}: (no run)"
    continue
  fi
  set -- ${RUN}
  echo "${V}: ${2} ${3} ${4}"
  api "repos/${REPO_SLUG}/actions/runs/${1}/jobs?per_page=50" | python3 -c '
import sys, json
for j in json.load(sys.stdin).get("jobs", []):
    print(f"    {j[\"name\"]:40s} {j[\"status\"]:12s} {j[\"conclusion\"] or \"-\"}")
'
done
