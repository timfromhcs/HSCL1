"""SHA256SUMS must use Unix line endings, or `sha256sum -c` fails on Linux.

The 0.1.5 and 0.1.6 releases shipped CRLF files because `make_release.py`/`release_split.py` were written on
Windows and used the default newline translation. `sha256sum -c` then treats the trailing "\\r" as part of
the file name and reports every line as a mismatch — the cloud verifier caught it on 0.1.6 (2026-11-11)
after the same bug had already been published once.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import release_split  # noqa: E402


def test_checksums_are_lf_and_match_the_parts(tmp_path):
    image = tmp_path / "img.bin"
    image.write_bytes(bytes(range(256)) * 20000)  # ~5 MB
    out = tmp_path / "out"

    assert release_split.main(["release_split.py", str(image), str(out), "1"]) == 0

    raw = (out / "SHA256SUMS").read_bytes()
    assert b"\r" not in raw, "SHA256SUMS must not contain CR: sha256sum -c would fail on Linux"

    lines = raw.decode("utf-8").splitlines()
    parts = sorted(p.name for p in out.glob("img.bin.part*"))
    assert len(parts) == len(lines) - 1, "one line per part plus the whole image"

    joined = b"".join((out / p).read_bytes() for p in parts)
    assert hashlib.sha256(joined).hexdigest() == hashlib.sha256(image.read_bytes()).hexdigest()
    assert lines[-1] == f"{hashlib.sha256(image.read_bytes()).hexdigest()}  img.bin"


def test_it_refuses_to_overwrite_existing_parts(tmp_path):
    image = tmp_path / "img.bin"
    image.write_bytes(b"x" * 4096)
    out = tmp_path / "out"
    assert release_split.main(["release_split.py", str(image), str(out), "1"]) == 0
    assert release_split.main(["release_split.py", str(image), str(out), "1"]) == 2
