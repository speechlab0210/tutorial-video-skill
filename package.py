#!/usr/bin/env python3
"""Package only Git-tracked, clean source files into a reproducible release ZIP."""
import argparse
import hashlib
import subprocess
import zipfile
from pathlib import Path


def package(output):
    root = Path(__file__).resolve().parent
    try:
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise SystemExit("git status failed (see any git error above); package.py is the "
                         "maintainer release script and must run inside a working git clone")
    if dirty:
        raise ValueError("commit or account for working-tree changes before packaging")
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    files = sorted(name.decode("utf-8") for name in raw.split(b"\0") if name)
    if not files:
        raise ValueError("no tracked files")
    output = Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("release archive must be outside source repository")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            path = root / name
            if path.is_symlink():
                raise ValueError("symlinks are not supported in the release")
            info = zipfile.ZipInfo("tutorial-video-skill/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("archive integrity check failed")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"{digest}  {output.name}")
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    package(parser.parse_args().output)
