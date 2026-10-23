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
  VERSIONS="$(grep -v '^#' "${HERE}/VERSIONS" | grep -v '^\s*$' | tr '\n' ' ')"
fi

api() {
  curl -sS -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" "https://api.github.com/$1"
}

# run-name is "Dart SDK <version> (eMudhra patched)"; newest runs come first.
RUNS_JSON="$(api "repos/${REPO_SLUG}/actions/workflows/${WORKFLOW}/runs?per_page=100")"
export RUNS_JSON VERSIONS
RUN_LINES="$(python3 - <<'PY'
import json, os
runs = json.loads(os.environ["RUNS_JSON"]).get("workflow_runs", [])
for v in os.environ["VERSIONS"].split():
    for r in runs:
        if r.get("display_title") == f"Dart SDK {v} (eMudhra patched)":
            print(v, r["id"], r["status"], r["conclusion"] or "-", r["html_url"])
            break
    else:
        print(v, "-", "(no run)", "-", "-")
PY
)"

while read -r V RUN_ID STATUS CONCLUSION URL; do
  echo "${V}: ${STATUS} ${CONCLUSION} ${URL}"
  [ "${RUN_ID}" != "-" ] || continue
  JOBS_JSON="$(api "repos/${REPO_SLUG}/actions/runs/${RUN_ID}/jobs?per_page=50")"
  JOBS_JSON="${JOBS_JSON}" python3 - <<'PY'
import json, os
for j in json.loads(os.environ["JOBS_JSON"]).get("jobs", []):
    print(f"    {j['name']:<44} {j['status']:<12} {j['conclusion'] or '-'}")
PY
done <<< "${RUN_LINES}"
