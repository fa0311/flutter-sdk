# eMudhra patch builds of the Dart SDK stable releases

**Unofficial.** This fork of [dart-lang/sdk](https://github.com/dart-lang/sdk)
rebuilds every Dart stable release of the past year (3.10.0 … 3.13.7) with the
two security fixes that upstream shipped in Dart 3.13.7 in response to the
compromised eMudhra (emSign) intermediate CA keys. It is not produced or
endorsed by Google or the Dart team.

## 日本語サマリ

- **何をしたか**: eMudhra (emSign) の中間 CA 秘密鍵漏洩への対応として Dart 3.13.7
  に入った 2 件の修正（Android 14+ での Conscrypt APEX ルートストア利用、侵害された
  中間 CA をブロックする BoringSSL への roll）を、過去 1 年分の stable タグ
  (3.10.0〜3.13.7) に cherry-pick し、GitHub Actions でビルドして Releases に置く。
- **ブランチ**: `stable-<version>-emudhra` = upstream タグ `<version>` + 2 コミット。
  `git diff <version> stable-<version>-emudhra` で差分を確認できる。
- **成果物**: Release `<version>-emudhra` に公式と同じ名前の
  `dartsdk-<os>-<arch>-release.zip`（linux x64/arm64、macos x64/arm64、windows x64）。
- **注意**: Flutter の `bin/cache/dart-sdk` を差し替えると `dart`/`flutter` CLI と
  standalone Dart は直るが、Flutter **アプリ**本体（Android/iOS/デスクトップ）は
  `dart:io` がエンジンに組み込まれているため、エンジンの再ビルドか Dart 3.13.7 を
  同梱した Flutter stable を待つ必要がある。

## Background

- Eight intermediate CA keys operated by eMudhra were reportedly compromised
  (multiple people independently recovered the private keys). Tracking issue:
  [dart-lang/sdk#64644 "[dart:io] Distrust eight compromised intermediate CA keys"](https://github.com/dart-lang/sdk/issues/64644).
- Go, rustls, Node.js, Chrome/Android (via a Play services blocklist update) and
  Windows (Disallowed CTL) all reject the keys explicitly. `dart:io` verifies
  certificates with its bundled BoringSSL on Linux, Windows and Android, so none
  of those OS-level blocklists protect Dart or Flutter programs there.
- Dart 3.13.7 (2026-10-22) fixed this on the stable channel with two
  cherry-picks. Flutter stable (3.47.x) still bundles Dart ≤ 3.13.5, and older
  Dart/Flutter lines will never receive the fix upstream.

## What is patched

Every branch `stable-<version>-emudhra` is the upstream tag `<version>` plus
exactly these two commits (3.13.7 already contains both, so that branch equals
the tag):

| # | Change | Upstream |
|---|--------|----------|
| 1 | `[dart:io]` Use Conscrypt APEX root store on Android 14+ (`runtime/bin/security_context_linux.cc`): read roots from `/apex/com.android.conscrypt/cacerts` when present so root CA distrusts pushed through Google Play system updates reach `dart:io`. | [dart-lang/sdk#64696](https://github.com/dart-lang/sdk/pull/64696), main [3ee784c4005](https://github.com/dart-lang/sdk/commit/3ee784c400517b44f4865531d1054c3df4363c9a), stable cherry-pick [568260](https://dart-review.googlesource.com/c/sdk/+/568260) |
| 2 | Roll BoringSSL (`DEPS` `boringssl_rev`) to `c7eb007fd10627f1abb41a3e368b85e24cd20af9`, the revision used by Dart 3.13.7 and main. It contains BoringSSL [dd682072baab "Block a handful of intermediate certificates"](https://boringssl.googlesource.com/boringssl/+/dd682072baab8029a83347e639d056c03e48d7e0), which rejects the eight compromised keys by SPKI SHA-256 hash during X.509 verification (`X509_V_ERR_CERT_REVOKED`), plus the X.509 path-builder fixes that landed with it. `third_party/boringssl/BUILD.gn` is identical on every patched tag and on main, so the roll is DEPS-only, exactly like upstream's stable cherry-pick. | stable cherry-pick [568261](https://dart-review.googlesource.com/c/sdk/+/568261) |

The BoringSSL roll commit also prepends a short section to `CHANGELOG.md`.
Nothing else is changed: `tools/VERSION` is untouched, so `dart --version`
reports the same version number as the official release (the git hash and
date identify the patched build).

## Versions, branches and releases

`emudhra/VERSIONS` lists the Dart stable tags released between 2025-10-23 and
2026-10-23. `emudhra/flutter_versions.txt` maps each of them to the Flutter
stable releases that bundle it (from Flutter's `releases_linux.json`).

| Dart | Flutter stable | Branch | Release |
|------|----------------|--------|---------|
| 3.10.0 | 3.38.0 – 3.38.2 | `stable-3.10.0-emudhra` | `3.10.0-emudhra` |
| 3.10.1 | 3.38.3 | `stable-3.10.1-emudhra` | `3.10.1-emudhra` |
| 3.10.2 | – | `stable-3.10.2-emudhra` | `3.10.2-emudhra` |
| 3.10.3 | 3.38.4 | `stable-3.10.3-emudhra` | `3.10.3-emudhra` |
| 3.10.4 | 3.38.5 | `stable-3.10.4-emudhra` | `3.10.4-emudhra` |
| 3.10.5 | – | `stable-3.10.5-emudhra` | `3.10.5-emudhra` |
| 3.10.6 | – | `stable-3.10.6-emudhra` | `3.10.6-emudhra` |
| 3.10.7 | 3.38.6 – 3.38.8 | `stable-3.10.7-emudhra` | `3.10.7-emudhra` |
| 3.10.8 | 3.38.9 | `stable-3.10.8-emudhra` | `3.10.8-emudhra` |
| 3.10.9 | 3.38.10 | `stable-3.10.9-emudhra` | `3.10.9-emudhra` |
| 3.11.0 | 3.41.0 – 3.41.2 | `stable-3.11.0-emudhra` | `3.11.0-emudhra` |
| 3.11.1 | 3.41.3, 3.41.4 | `stable-3.11.1-emudhra` | `3.11.1-emudhra` |
| 3.11.2 | – | `stable-3.11.2-emudhra` | `3.11.2-emudhra` |
| 3.11.3 | 3.41.5 | `stable-3.11.3-emudhra` | `3.11.3-emudhra` |
| 3.11.4 | 3.41.6 | `stable-3.11.4-emudhra` | `3.11.4-emudhra` |
| 3.11.5 | 3.41.7 – 3.41.9 | `stable-3.11.5-emudhra` | `3.11.5-emudhra` |
| 3.11.6 | – | `stable-3.11.6-emudhra` | `3.11.6-emudhra` |
| 3.12.0 | 3.44.0 | `stable-3.12.0-emudhra` | `3.12.0-emudhra` |
| 3.12.1 | 3.44.1 | `stable-3.12.1-emudhra` | `3.12.1-emudhra` |
| 3.12.2 | 3.44.2 – 3.44.9 | `stable-3.12.2-emudhra` | `3.12.2-emudhra` |
| 3.13.0 | 3.47.0 | `stable-3.13.0-emudhra` | `3.13.0-emudhra` |
| 3.13.1 | 3.47.1 | `stable-3.13.1-emudhra` | `3.13.1-emudhra` |
| 3.13.2 | 3.47.2 | `stable-3.13.2-emudhra` | `3.13.2-emudhra` |
| 3.13.3 | 3.47.3, 3.47.4 | `stable-3.13.3-emudhra` | `3.13.3-emudhra` |
| 3.13.4 | 3.47.5 | `stable-3.13.4-emudhra` | `3.13.4-emudhra` |
| 3.13.5 | 3.47.6, 3.47.7 | `stable-3.13.5-emudhra` | `3.13.5-emudhra` |
| 3.13.6 | – | `stable-3.13.6-emudhra` | `3.13.6-emudhra` |
| 3.13.7 | – (already fixed upstream; rebuilt unchanged) | `stable-3.13.7-emudhra` | `3.13.7-emudhra` |

## Using a build

Each release carries `dartsdk-<os>-<arch>-release.zip` (+ `.sha256sum`) with a
top-level `dart-sdk/` directory, the same layout as the official downloads.

- **Standalone Dart**: unzip and put `dart-sdk/bin` on `PATH`.
- **Flutter tooling**: replace `<flutter>/bin/cache/dart-sdk` with the
  `dart-sdk/` directory of the matching Dart version (see the table). This
  fixes the `dart` and `flutter` command line tools, `pub`, the analyzer, etc.
- **Flutter apps**: not fixed by this. On Android, iOS, macOS, Windows and
  Linux the `dart:io` networking code runs inside the Flutter engine
  (`libflutter.so`, `Flutter.framework`, `flutter_windows.dll`, …), which has to
  be rebuilt against a patched Dart, or you wait for a Flutter stable release
  that bundles Dart ≥ 3.13.7.

Platform notes:

- **Linux / Windows**: certificate chains are verified by the bundled
  BoringSSL, so the blocklist takes effect immediately. Dart ≤ 3.12 also
  carries a compiled-in copy of Mozilla's root store (used as a fallback on
  Linux, and in addition to the Windows root store on Windows); the blocklist
  rejects the compromised intermediates regardless of which roots are trusted.
- **macOS / iOS**: `dart:io` delegates chain validation to Apple's
  Security framework, so Apple's trust store and blocklist govern; the BoringSSL
  blocklist is not what rejects the chain there.
- **Android**: the Conscrypt APEX change matters only once a Flutter engine is
  built with it; the desktop SDK zips here do not contain Android binaries.

## Verifying

Source:

```sh
git fetch origin
git diff 3.10.9 origin/stable-3.10.9-emudhra          # exactly the two changes above
git log --format='%H %G? %s' 3.10.9..origin/stable-3.10.9-emudhra   # signed commits
```

Behaviour: the researchers who recovered the keys run a test server whose
chain goes through the compromised "EM DV TLS CA - G3B" intermediate
(SPKI SHA-256 `ebed6475…5105`, the third entry of the BoringSSL blocklist).
An unpatched Dart happily returns HTTP 200; a patched Dart fails the
handshake with `CERTIFICATE_VERIFY_FAILED`:

```dart
import 'dart:io';

void main() async {
  final client = HttpClient();
  try {
    final rq = await client.getUrl(Uri.parse('https://dv-g3b-emudhra.we-have-a-problem.com/'));
    final rs = await rq.close();
    print('HTTP ${rs.statusCode}  <-- NOT patched');
  } on HandshakeException catch (e) {
    print('rejected: $e  <-- patched');
  } finally {
    client.close();
  }
}
```

(This is the program from the gist that Flutter turned into its own
[handshake check devicelab test](https://github.com/flutter/flutter/pull/195113).)

## Building

### GitHub Actions

One workflow, `.github/workflows/build-dart-sdk.yml`, builds a single version
per run (input `version`) on

| Job | Runner | Output |
|-----|--------|--------|
| linux-x64 | `ubuntu-24.04` | `dartsdk-linux-x64-release.zip` |
| linux-arm64 | `ubuntu-24.04-arm` (native) | `dartsdk-linux-arm64-release.zip` |
| macos-arm64 | `macos-15` | `dartsdk-macos-arm64-release.zip` |
| macos-x64 | `macos-15-intel` | `dartsdk-macos-x64-release.zip` |
| windows-x64 | `windows-2022` (VS 2022, Windows SDK 10.0.26100) | `dartsdk-windows-x64-release.zip` |

and then a `release` job that creates or updates the GitHub release
`<version>-emudhra` with every zip that was built (a failed platform does not
block the others). Each job does the same thing the official bots do:
`depot_tools` → `gclient sync --no-history` → `tools/build.py --no-rbe --mode
release --arch <arch> create_sdk` → zip `dart-sdk/`. Expect roughly 1.5–3 hours
per platform on the free hosted runners.

```sh
export GITHUB_TOKEN=...            # needs workflow dispatch permission
emudhra/dispatch.sh                # all versions in emudhra/VERSIONS
emudhra/dispatch.sh 3.10.9 3.13.6  # or just some
emudhra/status.sh                  # latest run + job status per version
```

### Locally

```sh
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="$PWD/depot_tools:$PATH" DEPOT_TOOLS_UPDATE=0
mkdir dart && cd dart
git clone -b stable-3.10.9-emudhra https://github.com/fa0311/flutter-sdk-eMudhra.git sdk
cat > .gclient <<'G'
solutions = [{
  "name": "sdk",
  "url": "https://github.com/fa0311/flutter-sdk-eMudhra.git",
  "deps_file": "DEPS", "managed": False, "custom_deps": {},
  "custom_vars": {"download_reclient": False},
}]
G
gclient sync --no-history -D
cd sdk && ./tools/build.py --no-rbe --mode release --arch x64 create_sdk
out/ReleaseX64/dart-sdk/bin/dart --version
```

## Scripts in this directory

| File | Purpose |
|------|---------|
| `VERSIONS` | the Dart stable tags to patch (one per line) |
| `make_branches.sh` | (re)creates `stable-<version>-emudhra` for each version: cherry-picks the Conscrypt commit, rolls `boringssl_rev`, prepends the CHANGELOG note; signs commits when a GPG key is usable |
| `dispatch.sh` | triggers the GitHub Actions workflow for each version |
| `status.sh` | shows the latest run and job results for each version |
| `flutter_versions.txt` | Dart version → Flutter stable releases, used in the release notes |
