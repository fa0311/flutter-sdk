# eMudhra patch builds of the Dart SDK stable releases

**Unofficial.** This fork of [dart-lang/sdk](https://github.com/dart-lang/sdk)
rebuilds the newest patch release of each Dart stable line of the past year
(3.10.9, 3.11.6, 3.12.2 and 3.13.7) with the two security fixes that upstream
shipped in Dart 3.13.7 in response to the compromised eMudhra (emSign)
intermediate CA keys. Older patch releases of the same line (3.10.0 … 3.10.8,
…) are superseded by these builds and are not built separately. It is not produced or
endorsed by Google or the Dart team.

## 日本語サマリ

- **何をしたか**: eMudhra (emSign) の中間 CA 秘密鍵漏洩への対応として Dart 3.13.7
  に入った 2 件の修正（Android 14+ での Conscrypt APEX ルートストア利用、侵害された
  中間 CA をブロックする BoringSSL への roll）を、過去 1 年分の各 stable 系列の
  最新パッチ版 (3.10.9 / 3.11.6 / 3.12.2 / 3.13.7) に cherry-pick し、GitHub Actions
  でビルドして Releases に置く。同じ系列の古いパッチ版 (3.10.0〜3.10.8 など) は
  最新パッチ版で代替できるため個別には作らない。
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
Nothing else is changed: `tools/VERSION` is untouched.

**SDK hash.** The Dart VM, the kernel compiler and every snapshot embed an
"SDK hash" derived from `git rev-parse --short=10 HEAD`, and a VM refuses
kernels/snapshots produced by a build with a different hash
(`Invalid SDK hash`, `Wrong full snapshot version`). Flutter's engine build
compiles some kernels with the official prebuilt Dart SDK, and users mix
`bin/cache/dart-sdk`, `frontend_server` and engine binaries, so a patched
build with its own hash would not interoperate. Both workflows therefore
check out the patched branch and then `git reset --soft` HEAD to the
**upstream commit** (the tag, or the engine's `dart_revision`), keeping the
two fixes as working-tree changes. As a result `dart --version`,
`dart-sdk/revision` and the embedded SDK hash are *identical to the official
release*; the only way to tell a patched binary apart is its content, e.g.
with `emudhra/check_blocklist.py` (8/8 = patched, 0/8 = official).

## Versions, branches and releases

`emudhra/VERSIONS` lists the newest patch release of every Dart stable line
that had a release between 2025-10-23 and 2026-10-23. Because a newer patch
release supersedes the older ones of the same line, each build is the one to
use for *every* Flutter stable release on that Dart minor line.
`emudhra/flutter_versions.txt` maps each build to those Flutter releases (from
Flutter's `releases_linux.json`).

| Dart build | Covers Flutter stable (bundled Dart) | Branch | Release |
|------------|--------------------------------------|--------|---------|
| 3.10.9 | 3.38.0 – 3.38.10 (Dart 3.10.0 – 3.10.9) | `stable-3.10.9-emudhra` | `3.10.9-emudhra` |
| 3.11.6 | 3.41.0 – 3.41.9 (Dart 3.11.0 – 3.11.5) | `stable-3.11.6-emudhra` | `3.11.6-emudhra` |
| 3.12.2 | 3.44.0 – 3.44.9 (Dart 3.12.0 – 3.12.2) | `stable-3.12.2-emudhra` | `3.12.2-emudhra` |
| 3.13.7 | 3.47.0 – 3.47.7 (Dart 3.13.0 – 3.13.5) — already fixed upstream, rebuilt unchanged | `stable-3.13.7-emudhra` | `3.13.7-emudhra` |

Any other version can be produced the same way: add it to `emudhra/VERSIONS`
(or pass it on the command line), run `emudhra/make_branches.sh <version>`,
push the branch and dispatch the workflow.

## Using a build

Each release carries `dartsdk-<os>-<arch>-release.zip` (+ `.sha256sum`) with a
top-level `dart-sdk/` directory, the same layout as the official downloads.

- **Standalone Dart**: unzip and put `dart-sdk/bin` on `PATH`.
- **Flutter tooling**: replace `<flutter>/bin/cache/dart-sdk` with the
  `dart-sdk/` directory of the build for your Flutter release's Dart minor
  line (see the table; e.g. Flutter 3.38.x → 3.10.9). This
  fixes the `dart` and `flutter` command line tools, `pub`, the analyzer, etc.
- **Flutter apps**: not fixed by the Dart SDK zips. On Android, Linux and
  Windows the `dart:io` networking code runs inside the Flutter engine
  (`libflutter.so`, the GTK/Windows embedders), which has to be rebuilt against
  a patched Dart — see [Flutter apps: patched engine builds](#flutter-apps-patched-engine-builds)
  below — or you wait for a Flutter stable release that bundles Dart ≥ 3.13.7.

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

Binaries: `emudhra/check_blocklist.py` scans a file (or the binaries inside a
zip/jar, e.g. `libflutter.so` in an engine artifact) for the eight SPKI hashes
that BoringSSL's blocklist embeds. `8/8 ... OK` means the binary was built
with the fix; an official build reports `0/8 ... MISSING`. Because the
patched builds deliberately carry the official version string and SDK hash
(see above), this is the way to verify what you have:

```sh
python3 emudhra/check_blocklist.py dart-sdk/bin/dart
python3 emudhra/check_blocklist.py android-arm64-release/artifacts.zip
```

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

## Flutter apps: patched engine builds

Flutter *apps* do not use `bin/cache/dart-sdk` at run time: `dart:io` is
compiled into the Flutter engine (`libflutter.so` on Android, the GTK/Windows
embedders on desktop). The workflow `.github/workflows/build-flutter-engine.yml`
therefore rebuilds the engine of a Flutter stable release with the same two
fixes and publishes the artifacts as release `flutter-<version>-emudhra`.

Only platforms whose `dart:io` verifies TLS with BoringSSL are affected and
built: **Android** and **Linux** (Windows can be added the same way; iOS and
macOS delegate verification to Apple's Security framework and need nothing).

### How it works

- `emudhra/flutter_engines.txt` maps each Flutter stable version to its engine
  commit (`bin/internal/engine.version`) and to the Dart version that commit
  pins in `DEPS` (`dart_revision`):

  | Flutter | engine commit | pinned Dart | Dart branch used |
  |---------|---------------|-------------|------------------|
  | 3.47.7 | `deb287481e3c` | 3.13.5 | `stable-3.13.5-emudhra` |
  | 3.44.9 | `5a2a6a42cce6` | 3.12.2 | `stable-3.12.2-emudhra` |
  | 3.41.9 | `42d3d75a56ef` | 3.11.5 | `stable-3.11.5-emudhra` |
  | 3.38.10 | `cafcda5721a7` | 3.10.9 | `stable-3.10.9-emudhra` |

- The engine source is the **unmodified** engine commit. Only the `.gclient`
  file carries two overrides: `custom_deps` replaces
  `engine/src/flutter/third_party/dart` with the patched Dart branch (the exact
  Dart revision the engine pins, plus the two fixes), and `custom_vars` sets
  `dart_boringssl_rev` to `c7eb007fd106`. The engine's
  `third_party/boringssl/BUILD.gn` is identical to Dart's, so, as on the Dart
  side, the roll is DEPS-only.
- Each engine configuration is built exactly as Flutter's CI does: the gn
  flags, ninja targets and the list of archives to upload are read from
  `engine/src/flutter/ci/builders/*.json` of the checkout
  (`emudhra/engine_build_config.py`). One deliberate difference: Flutter CI
  ships the official *prebuilt* Dart SDK as `dart-sdk-<platform>.zip`
  (`--prebuilt-dart-sdk`), which would be unpatched, so configs that archive
  it (`host_debug`, `linux_debug_arm64`) are built with
  `--no-prebuilt-dart-sdk` and package the SDK built from the patched source. Default configs (`configs: all`):
  `android_{release,profile}_{arm64,x64}`, `android_{release,profile}` (arm),
  `android_debug{,_arm64,_x64,_x86}`, `host_debug`, `host_release`,
  `host_{debug,profile,release}_desktop`, `linux_{debug,profile,release}_arm64`.
- Because the engine commit is unchanged, the artifacts carry the official
  engine hash and the Maven artifacts (`download.flutter.io/io/flutter/...`)
  use the official coordinates `1.0.0-<engine hash>`. An unmodified Flutter SDK
  will therefore accept them when they are served through
  `FLUTTER_STORAGE_BASE_URL`.
- The `release` job restores the mirror tar already published for the
  version (if any), overlays the new artifacts, drops what the flutter tool
  never downloads (`impeller_sdk.zip`, `*-embedder.zip`, and the content-hash
  duplicates of the Maven artifacts — the Gradle plugin resolves
  `1.0.0-<engine commit>`), and arranges everything into the storage layout
  (`emudhra/make_mirror.py`) and publishes one tar
  (`flutter-engine-<version>-emudhra-mirror.tar`, split into `.part` files if
  it exceeds 1.9 GB), the per-config `symbols-<config>.zip` files, a listing
  and a `.sha256sum`.

### Using a patched engine

```sh
# 1. unpack the mirror tar from the release
mkdir mirror && tar -xf flutter-engine-3.47.7-emudhra-mirror.tar -C mirror

# 2. serve it; anything that is not in the mirror (fonts, gradle wrapper, ...)
#    is fetched from storage.googleapis.com on demand and cached
python3 emudhra/flutter_mirror.py --dir mirror --port 8181 &
export FLUTTER_STORAGE_BASE_URL=http://127.0.0.1:8181

# 3. drop the official engine artifacts the tool and Gradle already cached
rm -rf "$FLUTTER_ROOT/bin/cache/artifacts/engine" "$FLUTTER_ROOT/bin/cache"/*.stamp
rm -rf ~/.gradle/caches/modules-2/files-2.1/io.flutter \
       ~/.gradle/caches/modules-2/metadata-*/descriptors/io.flutter

# 4. re-download from the mirror and build
flutter precache --android --linux
flutter build apk --release        # keep FLUTTER_STORAGE_BASE_URL exported
```

Step 3 matters: the Flutter Gradle plugin resolves `io.flutter:arm64_v8a_release:1.0.0-<hash>`
from `$FLUTTER_STORAGE_BASE_URL/download.flutter.io`, and Gradle will happily
reuse an official jar it cached earlier under the same coordinates.

If you have your own static hosting, upload the `mirror/` directory there and
point `FLUTTER_STORAGE_BASE_URL` at it; the host must then also serve (or
proxy) the artifacts that were not rebuilt.

### Verified end to end

With an unmodified Flutter 3.47.7 SDK, `FLUTTER_STORAGE_BASE_URL` pointing at
`flutter_mirror.py` serving the `flutter-3.47.7-emudhra` mirror tar, and the
caches purged as above: `flutter --version` installed the patched
`bin/cache/dart-sdk` (8/8), `flutter precache --android` took every engine
artifact from the mirror (only `engine_stamp.json`, fonts and the gradle
wrapper came from the official storage), Gradle resolved
`io.flutter:arm64_v8a_release:1.0.0-<engine commit>` from the mirror, and the
resulting `flutter build apk --release` APK contains a `libflutter.so` with all
eight blocklist hashes.

### Running the engine workflow

```sh
export GITHUB_TOKEN=...
# all default configs for Flutter 3.47.7
curl -sS -X POST -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/fa0311/flutter-sdk-eMudhra/actions/workflows/build-flutter-engine.yml/dispatches \
  -d '{"ref":"main","inputs":{"flutter_version":"3.47.7","configs":"all","publish_release":"true"}}'
# or a subset
#   "configs":"android_release_arm64,host_debug"
```

Each config is one job on a free `ubuntu-24.04` runner: `gclient sync` of the
engine is about 15 GB and a few minutes; `android_release_arm64` took 28
minutes on a 16-core machine, so expect roughly 1.5–3 hours per config on the
4-core hosted runners. Re-running the workflow with a subset of configs
adds those artifacts to the existing release.

## Scripts in this directory

| File | Purpose |
|------|---------|
| `VERSIONS` | the Dart stable tags to patch (one per line) |
| `make_branches.sh` | (re)creates `stable-<version>-emudhra` for each version: cherry-picks the Conscrypt commit, rolls `boringssl_rev`, prepends the CHANGELOG note; signs commits when a GPG key is usable |
| `dispatch.sh` | triggers the GitHub Actions workflow for each version |
| `status.sh` | shows the latest run and job results for each version |
| `flutter_versions.txt` | Dart version → Flutter stable releases, used in the release notes |
| `flutter_engines.txt` | Flutter stable version → engine commit → pinned Dart version (engine workflow) |
| `engine_build_config.py` | reads gn flags / ninja targets of an engine config from `ci/builders/*.json` |
| `make_mirror.py` | arranges engine `zip_archives` into the `flutter_infra_release` / `download.flutter.io` layout |
| `flutter_mirror.py` | local `FLUTTER_STORAGE_BASE_URL` server with fallback to the official storage |
| `check_blocklist.py` | verifies that a binary / zip contains BoringSSL's blocklist of the eight compromised keys |
