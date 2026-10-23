#!/usr/bin/env python3
"""Serves a local Flutter artifact mirror with fallback to the official storage.

Point FLUTTER_STORAGE_BASE_URL at this server and the flutter tool (and the
Flutter Gradle plugin, which uses the same variable for download.flutter.io)
will fetch the patched engine artifacts from the mirror directory. Anything
that is not in the directory (fonts, gradle wrapper, artifacts that were not
rebuilt, ...) is fetched from https://storage.googleapis.com and cached, so
an unmodified Flutter SDK keeps working.

Usage: flutter_mirror.py --dir <mirror dir> [--port 8181] [--bind 127.0.0.1]
Then:  export FLUTTER_STORAGE_BASE_URL=http://127.0.0.1:8181
"""
import argparse
import http.server
import os
import shutil
import sys
import urllib.error
import urllib.request

UPSTREAM = "https://storage.googleapis.com"


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
            if not self._fetch(rel, local):
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

    def _fetch(self, rel, local):
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
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    p.add_argument("--port", type=int, default=8181)
    p.add_argument("--bind", default="127.0.0.1")
    a = p.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    handler = lambda *x, **k: Handler(*x, directory=os.path.abspath(a.dir), **k)  # noqa: E731
    srv = http.server.ThreadingHTTPServer((a.bind, a.port), handler)
    print(f"serving {os.path.abspath(a.dir)} on http://{a.bind}:{a.port} (fallback: {UPSTREAM})")
    print(f"export FLUTTER_STORAGE_BASE_URL=http://{a.bind}:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
