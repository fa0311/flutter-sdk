#!/usr/bin/env python3
"""Prints the gn arguments and ninja targets of one engine CI build.

The Flutter engine's CI builds are described in engine/src/flutter/ci/builders/
*.json. Reading them at build time keeps this workflow version-agnostic: the
exact gn flags and ninja targets of each Flutter release are used.

Usage: engine_build_config.py <engine/src/flutter/ci/builders dir> <config>
Writes KEY=VALUE lines (BUILDER_FILE, GN_ARGS, NINJA_TARGETS, OUT_DIR,
ARCHIVE_PATHS) that can be appended to $GITHUB_ENV. ARCHIVE_PATHS lists the
files/directories CI uploads, relative to out/<OUT_DIR>/zip_archives/.
"""
import glob
import json
import os
import sys

builders_dir, config = sys.argv[1], sys.argv[2]
wanted = {config, "ci/" + config, "ci\\" + config}
for path in sorted(glob.glob(os.path.join(builders_dir, "*.json"))):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for build in data.get("builds", []):
        if build.get("name") not in wanted:
            continue
        gn = [a for a in build.get("gn", []) if a not in ("--rbe", "--goma")]
        if "--no-goma" not in gn:
            gn.append("--no-goma")
        # Always build into out/ci/<config>, like CI does.
        if "--target-dir" not in gn:
            gn += ["--target-dir", "ci/" + config]
        targets = build.get("ninja", {}).get("targets", [])
        out_dir = build.get("ninja", {}).get("config", "ci/" + config)
        # The files CI uploads, relative to out/<out_dir>/zip_archives/.
        prefix = "out/" + out_dir + "/zip_archives/"
        archives = []
        for a in build.get("archives", []):
            for ip in a.get("include_paths", []):
                archives.append(ip[len(prefix):] if ip.startswith(prefix) else ip)
        # Flutter CI ships the *prebuilt* (official, unpatched) Dart SDK as
        # dart-sdk-<platform>.zip. Configs that archive it must build the SDK
        # from the patched source instead.
        if any(os.path.basename(a).startswith("dart-sdk-") for a in archives) and "--prebuilt-dart-sdk" in gn:
            gn = [a for a in gn if a != "--prebuilt-dart-sdk"] + ["--no-prebuilt-dart-sdk"]
            print("NOTE=dart-sdk archive requested: building the Dart SDK from source (--no-prebuilt-dart-sdk)", file=sys.stderr)
        print("BUILDER_FILE=" + os.path.basename(path))
        print("GN_ARGS=" + " ".join(gn))
        print("NINJA_TARGETS=" + " ".join(targets))
        print("OUT_DIR=" + out_dir)
        print("ARCHIVE_PATHS=" + " ".join(archives))
        sys.exit(0)
print(f"config {config!r} not found in {builders_dir}", file=sys.stderr)
sys.exit(1)
