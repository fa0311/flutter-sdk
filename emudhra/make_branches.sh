#!/usr/bin/env bash
# Creates (or recreates) one branch per Dart stable tag with the two eMudhra
# related fixes from Dart 3.13.7 applied on top:
#
#   1. [dart:io] Use Conscrypt APEX root store on Android 14+
#      main:   3ee784c400517b44f4865531d1054c3df4363c9a
#      stable: a9e26a21af3 (https://dart-review.googlesource.com/c/sdk/+/568260)
#   2. Roll BoringSSL to c7eb007fd10627f1abb41a3e368b85e24cd20af9, which picks up
#      BoringSSL dd682072baab "Block a handful of intermediate certificates"
#      (the eight compromised eMudhra/emSign intermediate CA keys).
#      stable: ecb2c835161 (https://dart-review.googlesource.com/c/sdk/+/568261)
#
# Usage: emudhra/make_branches.sh [VERSION...]
#   With no arguments every version listed in emudhra/VERSIONS is processed.
#   Branch name: stable-<version>-emudhra
#
# The script works in a dedicated git worktree so the main checkout is left
# untouched. Existing branches are reset to the tag and re-patched.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREE="${EMUDHRA_WORKTREE:-${REPO}/../_emudhra-build/patchwork}"
CONSCRYPT_COMMIT=3ee784c400517b44f4865531d1054c3df4363c9a
BORINGSSL_NEW=c7eb007fd10627f1abb41a3e368b85e24cd20af9
BORINGSSL_BLOCK_COMMIT=dd682072baab8029a83347e639d056c03e48d7e0
TRAILER='Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'

# Sign commits when a GPG key is usable non-interactively; otherwise fall back
# to unsigned commits so the script also works on machines without the key.
if git config --get user.signingkey >/dev/null 2>&1 \
   && echo test | gpg --batch --pinentry-mode error --clearsign >/dev/null 2>&1; then
  GPGSIGN=true
else
  GPGSIGN=false
fi
echo "commit signing: ${GPGSIGN}"
git_() { git -c "commit.gpgsign=${GPGSIGN}" "$@"; }

if [ $# -gt 0 ]; then
  VERSIONS="$*"
else
  VERSIONS="$(grep -v '^#' "${REPO}/emudhra/VERSIONS" | grep -v '^\s*$')"
fi

if [ ! -d "${WORKTREE}" ]; then
  mkdir -p "$(dirname "${WORKTREE}")"
  git -C "${REPO}" worktree add --detach "${WORKTREE}" main
fi
cd "${WORKTREE}"

for V in ${VERSIONS}; do
  BRANCH="stable-${V}-emudhra"
  echo "=== ${V} -> ${BRANCH}"
  git_ checkout -q --detach "refs/tags/${V}"
  git_ checkout -q -B "${BRANCH}"

  # 1. Conscrypt APEX root store (Android 14+).
  if git merge-base --is-ancestor "${CONSCRYPT_COMMIT}" HEAD; then
    echo "    conscrypt: already included"
  else
    git_ cherry-pick --no-commit "${CONSCRYPT_COMMIT}"
    MSG="$(git log -1 --format=%B "${CONSCRYPT_COMMIT}")"
    MSG="${MSG}"$'\n'"(cherry picked from commit ${CONSCRYPT_COMMIT})"$'\n\n'"${TRAILER}"
    git_ commit -q --author="$(git log -1 --format='%an <%ae>' "${CONSCRYPT_COMMIT}")" -m "${MSG}"
    echo "    conscrypt: cherry-picked"
  fi

  # 2. BoringSSL roll.
  OLD="$(grep -oE '"boringssl_rev": "[0-9a-f]{40}"' DEPS | grep -oE '[0-9a-f]{40}')"
  if [ "${OLD}" = "${BORINGSSL_NEW}" ]; then
    echo "    boringssl: already at ${BORINGSSL_NEW:0:12}"
  else
    sed -i "s/\"boringssl_rev\": \"${OLD}\"/\"boringssl_rev\": \"${BORINGSSL_NEW}\"/" DEPS
    grep -q "\"boringssl_rev\": \"${BORINGSSL_NEW}\"" DEPS
    python3 - "${V}" <<'PY'
import sys, datetime
v = sys.argv[1]
today = datetime.date.today().isoformat()
section = f"""## {v} (unofficial eMudhra patch build)

**Built on:** {today}

This is an unofficial rebuild of Dart {v} with the two security fixes from
Dart 3.13.7 applied (see https://github.com/fa0311/flutter-sdk-eMudhra):

- Uses the updatable Conscrypt APEX root certificate store on Android 14+ in
  `dart:io`, so that root CA additions and distrusts delivered via Google Play
  system updates are honored. (issue [#64696])
- Updates BoringSSL to pick up upstream security fixes, including blocking a
  number of compromised intermediate certificates and X.509 path validation
  fixes. (issue [#568000], [dart-lang/sdk#64644])

[#64696]: https://github.com/dart-lang/sdk/pull/64696
[#568000]: https://dart-review.googlesource.com/c/sdk/+/568000
[dart-lang/sdk#64644]: https://github.com/dart-lang/sdk/issues/64644

"""
with open("CHANGELOG.md", encoding="utf-8") as f:
    body = f.read()
with open("CHANGELOG.md", "w", encoding="utf-8") as f:
    f.write(section + body)
PY
    git_ add DEPS CHANGELOG.md
    git_ commit -q -F - <<MSG
[stable] Roll BoringSSL from ${OLD:0:12} to ${BORINGSSL_NEW:0:12}

https://boringssl.googlesource.com/boringssl.git/+log/${OLD:0:12}..${BORINGSSL_NEW:0:12}

Picks up BoringSSL ${BORINGSSL_BLOCK_COMMIT:0:12} "Block a handful of
intermediate certificates", which rejects the eight compromised
eMudhra (emSign) intermediate CA keys by SPKI hash, plus the X.509 path
validation fixes that landed with it.

This mirrors the Dart 3.13.7 stable cherry-pick
https://dart-review.googlesource.com/c/sdk/+/568261
(Change-Id: I806410e41b63766fe8f93fdee35729986927c230) on top of ${V}.
DEPS-only roll: third_party/boringssl/BUILD.gn is identical on ${V} and
main.

Issue: https://github.com/dart-lang/sdk/issues/64644

${TRAILER}
MSG
    echo "    boringssl: rolled ${OLD:0:12} -> ${BORINGSSL_NEW:0:12}"
  fi
  echo "    $(git log --oneline "refs/tags/${V}..HEAD" | wc -l) commit(s) on top of ${V}"
done
git_ checkout -q --detach
echo "done"
