#!/usr/bin/env python3
"""Arranges engine zip_archives into the layout of Flutter's artifact storage.

The engine build writes its archives to out/<config>/zip_archives/ using the
same relative layout as storage.googleapis.com/flutter_infra_release/flutter/
<engine hash>/, except for the Maven artifacts, which live under
zip_archives/download.flutter.io/ and are served from
<base>/download.flutter.io/. This script copies a set of zip_archives
directories into one tree that can be served as FLUTTER_STORAGE_BASE_URL.
Files already present in --out (e.g. extracted from a previous release's
mirror tar) are replaced by the new copies.

Usage: make_mirror.py --engine-commit <hash> --out <dir> [--skip-symbols]
                      <zip_archives dir>...
"""
import argparse
import os
import shutil
import sys

p = argparse.ArgumentParser()
p.add_argument("--engine-commit", required=True)
p.add_argument("--out", required=True)
p.add_argument("--skip-symbols", action="store_true",
               help="leave out symbols.zip files (large, not downloaded by the flutter tool)")
p.add_argument("--keep-extras", action="store_true",
               help="keep files the flutter tool never downloads (impeller_sdk.zip, *-embedder.zip) and the "
                    "content-hash duplicates of the Maven artifacts")
p.add_argument("dirs", nargs="+")
args = p.parse_args()

copied = []
for d in args.dirs:
    d = d.rstrip("/")
    if not os.path.isdir(d):
        print(f"skip {d}: not a directory", file=sys.stderr)
        continue
    for root, _, files in os.walk(d):
        for name in files:
            src = os.path.join(root, name)
            rel = os.path.relpath(src, d)
            if args.skip_symbols and name == "symbols.zip":
                continue
            if rel.startswith("download.flutter.io" + os.sep):
                dst_rel = rel
            else:
                dst_rel = os.path.join("flutter_infra_release", "flutter", args.engine_commit, rel)
            dst = os.path.join(args.out, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                print(f"note: replacing existing {dst_rel}", file=sys.stderr)
            shutil.copy2(src, dst)
            copied.append((os.path.getsize(src), dst_rel))

copied.sort(key=lambda t: t[1])
for size, rel in copied:
    print(f"{size:>12}  copied {rel}", file=sys.stderr)
print(f"{sum(s for s, _ in copied):>12}  COPIED ({len(copied)} files)", file=sys.stderr)


def is_extra(rel):
    """Files that are large and never requested by the flutter tool / Gradle."""
    name = os.path.basename(rel)
    if name == "impeller_sdk.zip" or name.endswith("-embedder.zip"):
        return True
    if rel.startswith("download.flutter.io" + os.sep) and name != "maven-metadata.xml":
        # The engine emits every Maven artifact twice: 1.0.0-<engine commit> (what
        # the Flutter Gradle plugin resolves, from bin/cache/engine.stamp) and
        # 1.0.0-<content hash>. Keep only the engine-commit one.
        return "1.0.0-" in name and args.engine_commit not in name
    return False


# Prune over the whole output tree so that files restored from an earlier
# release tar are pruned too.
if not args.keep_extras:
    pruned = []
    for root, _, files in os.walk(args.out):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, args.out)
            if is_extra(rel):
                pruned.append((os.path.getsize(full), rel))
                os.remove(full)
    for size, rel in sorted(pruned, key=lambda t: t[1]):
        print(f"{size:>12}  PRUNED {rel}", file=sys.stderr)
    print(f"{sum(s for s, _ in pruned):>12}  PRUNED ({len(pruned)} files)", file=sys.stderr)

# stdout: the complete listing of the mirror tree (saved next to the release).
kept = []
for root, _, files in os.walk(args.out):
    for name in files:
        full = os.path.join(root, name)
        kept.append((os.path.getsize(full), os.path.relpath(full, args.out)))
for size, rel in sorted(kept, key=lambda t: t[1]):
    print(f"{size:>12}  {rel}")
print(f"{sum(s for s, _ in kept):>12}  TOTAL ({len(kept)} files in mirror)")
