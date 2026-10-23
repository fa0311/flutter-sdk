#!/usr/bin/env python3
"""Checks that a binary contains BoringSSL's compromised-intermediate blocklist.

BoringSSL dd682072 ("Block a handful of intermediate certificates") embeds the
SHA-256 SPKI hashes of the eight compromised eMudhra intermediate CA keys in
crypto/x509/x509_vfy.cc. Any binary that links that BoringSSL (dart, dartvm,
libflutter.so, flutter_tester, ...) carries the 8 x 32-byte table in its
read-only data, so scanning for it is a quick way to verify that an artifact
was really built with the fix.

Usage: check_blocklist.py <file>...   (zip files are scanned inside)
Exit status is 0 when every file contains all eight hashes.
"""
import sys
import zipfile

HASHES = [
    "e0254c7fcdc265e2f0f8a428dabb75ab4ae039b4872d62f5ee57f0877d5a8a41",
    "43bffa19d6ef651451f6841e019931e96f6f2eaeff28ab4b6f1ce4576de2717b",
    "ebed6475c2c2d80fcb199f3fe8dd6e6b3ce60b77eb15d4e42c3dec0c6f5b5105",  # EM DV TLS CA - G3B
    "5c0660a2b164910d8ff589c18e14552e9e0ec237dcefe2cb736d41a4811f81a0",
    "63ecefee431d49523bc1136c4e72d0206a477086caf606cd5cf025686c109cf8",
    "49dd353dc2b919a3770645117d0e60c16115e7d1bc259eefe734b00ea434fe5f",
    "ec4ffa1ad0ac88081314b7aaffef6a91f97cd57291bb5ba686c5415f5eb4f6b6",
    "92c063d67e8f14db71d288e11266ffdaf69cbf115f7bab14f3bc2f68d25e0e30",
]
NEEDLES = [bytes.fromhex(h) for h in HASHES]
EXECUTABLES = {"dart", "dartvm", "dartaotruntime", "flutter_tester", "gen_snapshot",
               "dart.exe", "dartaotruntime.exe", "flutter_tester.exe", "gen_snapshot.exe"}
LIBRARY_SUFFIXES = (".so", ".dll", ".dylib", ".jar", ".zip")


def scan(data):
    return sum(1 for n in NEEDLES if n in data)


def scan_zip(path):
    results = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            base = name.rsplit("/", 1)[-1]
            if info.is_dir() or (base not in EXECUTABLES and not base.endswith(LIBRARY_SUFFIXES)):
                continue
            data = z.read(info)
            if base.endswith((".jar", ".zip")):
                import io
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as inner:
                        for ii in inner.infolist():
                            ib = ii.filename.rsplit("/", 1)[-1]
                            if ib in EXECUTABLES or ib.endswith((".so", ".dll", ".dylib")):
                                results.append((f"{name}!{ii.filename}", scan(inner.read(ii))))
                except zipfile.BadZipFile:
                    pass
                continue
            results.append((name, scan(data)))
    return results


def main():
    ok = True
    for path in sys.argv[1:]:
        if zipfile.is_zipfile(path):
            found = scan_zip(path)
            if not found:
                print(f"{path}: no binaries to scan inside")
                ok = False
            for name, n in found:
                print(f"{path}!{name}: {n}/8 blocklist hashes {'OK' if n == 8 else 'MISSING'}")
                ok &= n == 8
        else:
            with open(path, "rb") as f:
                n = scan(f.read())
            print(f"{path}: {n}/8 blocklist hashes {'OK' if n == 8 else 'MISSING'}")
            ok &= n == 8
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
