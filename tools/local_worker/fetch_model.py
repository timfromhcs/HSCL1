#!/usr/bin/env python3
"""Fetch one GGUF file from Hugging Face with SHA-256 verification (plan L, task L1).

The expected digest comes from the host's own tree API (LFS oid), never from the downloaded bytes. Downloads are resumable
through a `.part` file, verified, and either renamed into place or deleted. The destination must lie inside the allowed root
(default `C:\\LocalAIBACKEND`). Nothing is executed; the result is data.

Usage: python fetch_model.py REPO FILE [--dest DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Callable, Iterator

DEFAULT_ROOT = Path(r"C:\LocalAIBACKEND")  # the gateway resolves model files relative to this folder
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._()+-]{0,200}\.gguf$")
CHUNK = 1024 * 1024
UA = "hscl1-local-worker/0.1"


def _http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - https URL built from validated parts
        return json.load(r)


def _http_download(url: str, start_byte: int) -> Iterator[bytes]:
    headers = {"User-Agent": UA}
    if start_byte:
        headers["Range"] = f"bytes={start_byte}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        if start_byte and r.status != 206:
            raise ValueError("server ignored the Range request; delete the .part file and retry")
        while True:
            block = r.read(CHUNK)
            if not block:
                return
            yield block


def expected_sha256(repo: str, filename: str, api_get: Callable[[str], list] = _http_json) -> str:
    tree = api_get(f"https://huggingface.co/api/models/{repo}/tree/main")
    for entry in tree:
        if entry.get("path") == filename and entry.get("type") == "file":
            oid = (entry.get("lfs") or {}).get("oid")
            if not oid or not re.fullmatch(r"[0-9a-f]{64}", oid):
                raise ValueError(f"{filename}: the host publishes no sha256 digest for this file")
            return oid
    raise ValueError(f"{filename}: not found in {repo}")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def fetch(
    repo: str,
    filename: str,
    dest_dir: Path,
    allowed_root: Path = DEFAULT_ROOT,
    api_get: Callable[[str], list] = _http_json,
    download: Callable[[str, int], Iterator[bytes]] = _http_download,
) -> Path:
    if not REPO_RE.fullmatch(repo):
        raise ValueError(f"bad repo id: {repo!r}")
    if not FILE_RE.fullmatch(filename):
        raise ValueError(f"bad file name: {filename!r}")
    dest_dir = Path(dest_dir).resolve()
    root = Path(allowed_root).resolve()
    if dest_dir != root and root not in dest_dir.parents:
        raise ValueError(f"destination {dest_dir} is outside the allowed root {root}")
    want = expected_sha256(repo, filename, api_get)
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / filename
    if final.exists() and _sha256_file(final) == want:
        return final
    part = dest_dir / (filename + ".part")
    start = part.stat().st_size if part.exists() else 0
    mode = "ab" if start else "wb"
    with part.open(mode) as f:
        for block in download(f"https://huggingface.co/{repo}/resolve/main/{filename}", start):
            f.write(block)
    got = _sha256_file(part)
    if got != want:
        part.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise ValueError(f"sha256 mismatch for {filename}: expected {want}, got {got}")
    part.replace(final)
    return final


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo")
    ap.add_argument("file")
    ap.add_argument("--dest", type=Path, default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    try:
        p = fetch(a.repo, a.file, a.dest)
    except (ValueError, OSError) as e:
        print(f"fetch_model: {e}", file=sys.stderr)
        return 2
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
