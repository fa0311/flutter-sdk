#!/usr/bin/env python3
"""Serves a patched Flutter engine mirror as FLUTTER_STORAGE_BASE_URL.

    python3 flutter_mirror.py --release 3.47.7      # fetch the mirror from the
                                                    # GitHub release once, then serve it
    python3 flutter_mirror.py --dir ./mirror        # serve an already extracted mirror

Point FLUTTER_STORAGE_BASE_URL at the server (http://127.0.0.1:8181 by
default) and the flutter tool, and the Flutter Gradle plugin, fetch the patched
engine artifacts from it. Anything that is not in the mirror (fonts, the gradle
wrapper, artifacts that were not rebuilt, ...) is fetched from
https://storage.googleapis.com and cached, so an unmodified Flutter SDK keeps
working. Standard library only.
"""
import argparse
import hashlib
import http.server
import os
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.request

UPSTREAM = "https://storage.googleapis.com"
DEFAULT_REPO = "fa0311/flutter-sdk-eMudhra"


# --------------------------------------------------------------------------
# fetching the mirror from a GitHub release
# --------------------------------------------------------------------------
def _fetch(url, dest=None):
    """Downloads url to dest (streaming, with a progress line) or returns the body."""
    with urllib.request.urlopen(url, timeout=120) as resp:
        if dest is None:
            return resp.read().decode()
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {os.path.basename(dest)}: {done / 1e6:.0f}/{total / 1e6:.0f} MB", end="", file=sys.stderr)
        print(file=sys.stderr)
        os.replace(tmp, dest)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class _Chained:
    """A read-only stream over several files in sequence (the split tar parts)."""

    def __init__(self, paths):
        self.paths = list(paths)
        self.f = None

    def read(self, n=-1):
        out = b""
        while n < 0 or len(out) < n:
            if self.f is None:
                if not self.paths:
                    break
                self.f = open(self.paths.pop(0), "rb")
            chunk = self.f.read(n - len(out) if n >= 0 else 1 << 20)
            if not chunk:
                self.f.close()
                self.f = None
                continue
            out += chunk
        return out

    def close(self):
        if self.f:
            self.f.close()


def fetch_release_mirror(version, repo, cache_root):
    """Returns the directory holding the extracted mirror of release flutter-<version>-emudhra."""
    base = f"https://github.com/{repo}/releases/download/flutter-{version}-emudhra"
    d = os.path.join(cache_root, version)
    mirror = os.path.join(d, "mirror")
    if os.path.exists(os.path.join(d, ".complete")):
        return mirror
    os.makedirs(d, exist_ok=True)
    print(f"fetching the Flutter {version} engine mirror from {base}", file=sys.stderr)
    try:
        sums = _fetch(f"{base}/flutter-engine-{version}-emudhra.sha256sum")
    except urllib.error.HTTPError as e:
        sys.exit(f"no release flutter-{version}-emudhra at {base} ({e.code})")
    parts = []
    pat = re.compile(rf"flutter-engine-{re.escape(version)}-emudhra-mirror\.tar(\.\d+\.part)?$")
    for line in sums.splitlines():
        digest, name = line.split(None, 1)
        name = name.strip().lstrip("*")
        name = name[2:] if name.startswith("./") else name
        if pat.match(name):
            parts.append((name, digest))
    parts.sort()
    if not parts:
        sys.exit("the release has no mirror tar")
    for name, digest in parts:
        path = os.path.join(d, name)
        if not (os.path.exists(path) and _sha256(path) == digest):
            _fetch(f"{base}/{name}", path)
            if _sha256(path) != digest:
                sys.exit(f"checksum mismatch for {name}")
    print("  checksums OK; extracting", file=sys.stderr)
    shutil.rmtree(mirror, ignore_errors=True)
    os.makedirs(mirror)
    stream = _Chained(os.path.join(d, name) for name, _ in parts)
    with tarfile.open(mode="r|", fileobj=stream) as tf:
        try:
            tf.extractall(mirror, filter="data")
        except TypeError:  # Python < 3.12
            tf.extractall(mirror)
    stream.close()
    for name, _ in parts:
        os.remove(os.path.join(d, name))
    open(os.path.join(d, ".complete"), "w").close()
    return mirror


# --------------------------------------------------------------------------
# serving
# --------------------------------------------------------------------------
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self._serve(send_body=True)

    def do_HEAD(self):
        self._serve(send_body=False)

    def _serve(self, send_body):
        rel = self.path.split("?", 1)[0].lstrip("/")
        if ".." in rel.split("/"):
            self.send_error(400)
            return
        local = os.path.join(self.directory, rel)
        if not os.path.isfile(local):
            if not self._fetch_upstream(rel, local):
                return
            self.log_message("fetched from upstream: %s", rel)
        else:
            self.log_message("local: %s", rel)
        size = os.path.getsize(local)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        if send_body:
            with open(local, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

    def _fetch_upstream(self, rel, local):
        url = f"{UPSTREAM}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                os.makedirs(os.path.dirname(local), exist_ok=True)
                tmp = local + ".part"
                with open(tmp, "wb") as f:
                    shutil.copyfileobj(resp, f)
                os.replace(tmp, local)
            return True
        except urllib.error.HTTPError as e:
            self.send_error(e.code, f"upstream {url}: {e.reason}")
        except Exception as e:  # noqa: BLE001
            self.send_error(502, f"upstream {url}: {e}")
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--release", metavar="FLUTTER_VERSION",
                     help="fetch (once) and serve the mirror of release flutter-<version>-emudhra")
    src.add_argument("--dir", help="serve this already extracted mirror directory")
    p.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repository of the releases (default {DEFAULT_REPO})")
    p.add_argument("--cache-dir", default=os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "emudhra-flutter-mirror"),
                   help="where --release keeps the mirrors (default ~/.cache/emudhra-flutter-mirror)")
    p.add_argument("--port", type=int, default=8181)
    p.add_argument("--bind", default="127.0.0.1")
    a = p.parse_args()
    directory = fetch_release_mirror(a.release, a.repo, a.cache_dir) if a.release else a.dir
    directory = os.path.abspath(directory)
    os.makedirs(directory, exist_ok=True)
    handler = lambda *x, **k: Handler(*x, directory=directory, **k)  # noqa: E731
    srv = http.server.ThreadingHTTPServer((a.bind, a.port), handler)
    print(f"serving {directory} on http://{a.bind}:{a.port} (fallback: {UPSTREAM})")
    print(f"export FLUTTER_STORAGE_BASE_URL=http://{a.bind}:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
