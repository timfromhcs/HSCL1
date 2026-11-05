#!/usr/bin/env python3
"""Write ISO.manifest.json next to a freshly built ISO.

Usage: write_iso_manifest.py ISO VERSION QA(0|1) BASE_ISO_SHA256 GIT_COMMIT GIT_DIRTY(0|1)
The values describe the build; the ISO hash and size are computed from the actual file.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(iso: Path, version: str, qa: bool, base_sha: str, commit: str, dirty: bool) -> dict:
    return {
        "product": "HSCL1",
        "artifact": iso.name,
        "version": version,
        "workshop_default": "disabled",  # attested: the builder only gets here after verify-image.sh proved Workshop is inert
        "qa_image": qa,
        "base": "Kubuntu 26.04.1 desktop amd64 (Ubuntu resolute)",
        "base_iso_sha256": base_sha,
        "git_commit": commit,
        "git_dirty": dirty,
        "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iso_bytes": iso.stat().st_size,
        "iso_sha256": sha256(iso),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        print(__doc__)
        return 2
    iso = Path(argv[1])
    if not iso.is_file():
        print(f"no such ISO: {iso}")
        return 2
    m = build(iso, argv[2], argv[3] == "1", argv[4], argv[5], argv[6] == "1")
    out = iso.with_name(iso.name + ".manifest.json")
    out.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
