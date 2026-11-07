"""release-split.sh / release-join.sh: round trip, tamper detection, safety checks (small files, tiny part size).

Runs through `tests/shellutil.py`, so the release tooling is exercised on Linux CI, in WSL and with Git Bash on Windows
instead of being skipped on the host.
"""
import hashlib
import os
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SPLIT = ROOT / "scripts/release-split.sh"
JOIN = ROOT / "scripts/release-join.sh"
pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


def run(script, *args, **env):
    converted = [shellutil.to_bash_path(a) if isinstance(a, Path) else str(a) for a in args]
    return shellutil.run_script(script, *converted, env_overrides=env or None)


@pytest.fixture()
def parts(tmp_path):
    img = tmp_path / "IMG.iso"
    img.write_bytes(os.urandom(10_000))
    out = tmp_path / "out"
    r = run(SPLIT, img, out, PART_BYTES="3000")
    assert r.returncode == 0, r.stderr
    return img, out


def test_split_makes_ordered_parts_and_sums(parts):
    img, out = parts
    names = sorted(p.name for p in out.glob("IMG.iso.part*"))
    assert names == ["IMG.iso.part000", "IMG.iso.part001", "IMG.iso.part002", "IMG.iso.part003"]
    sums = (out / "SHA256SUMS").read_text().splitlines()
    assert len(sums) == 5 and sums[-1].split()[-1].lstrip("*") == "IMG.iso"  # coreutils marks binary mode with *
    assert sums[-1].split()[0] == hashlib.sha256(img.read_bytes()).hexdigest()


def test_join_roundtrip_is_bit_identical(parts):
    img, out = parts
    r = run(JOIN, out)
    assert r.returncode == 0, r.stderr + r.stdout
    assert (out / "IMG.iso").read_bytes() == img.read_bytes()
    assert not list(out.glob("*.joining"))


def test_verify_only_writes_nothing(parts):
    _img, out = parts
    r = run(JOIN, out, "--verify-only")
    assert r.returncode == 0 and "verify-only" in r.stdout
    assert not (out / "IMG.iso").exists()


def test_tampered_part_is_rejected(parts):
    _img, out = parts
    p = out / "IMG.iso.part001"
    data = bytearray(p.read_bytes())
    data[5] ^= 0xFF
    p.write_bytes(bytes(data))
    r = run(JOIN, out)
    assert r.returncode != 0 and not (out / "IMG.iso").exists()


def test_missing_part_and_wrong_whole_hash_are_rejected(parts):
    img, out = parts
    (out / "IMG.iso.part002").unlink()
    assert run(JOIN, out).returncode != 0
    out2 = out.parent / "out2"
    assert run(SPLIT, img, out2, PART_BYTES="4000").returncode == 0
    lines = (out2 / "SHA256SUMS").read_text().splitlines()
    lines[-1] = "0" * 64 + "  IMG.iso"
    (out2 / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    r = run(JOIN, out2)
    assert r.returncode != 0 and not (out2 / "IMG.iso").exists()


def test_existing_target_needs_force_and_split_refuses_overwrite(parts):
    img, out = parts
    assert run(JOIN, out).returncode == 0
    assert run(JOIN, out).returncode == 2
    assert run(JOIN, out, "--force").returncode == 0
    assert run(SPLIT, img, out, PART_BYTES="3000").returncode == 2


def test_part_size_limit_and_bad_input():
    assert run(SPLIT, __file__, "x", "2000").returncode == 2
    assert run(SPLIT, "does-not-exist", "x").returncode == 2
    assert run(JOIN, "does-not-exist").returncode == 2
