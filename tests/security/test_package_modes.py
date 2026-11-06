"""build-deb.sh must normalise payload modes by content, not trust the checkout (NTFS reports 0777 for everything).

Runs the real script with a stand-in `dpkg-deb` that records the staged modes. Needs a POSIX filesystem that honours chmod, so it is
skipped on Windows checkouts (narrow, documented skip); CI on Linux always runs it.
"""
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="needs a filesystem that honours chmod (Linux CI runs this)")


def test_payload_modes_are_derived_from_content(tmp_path):
    shim = tmp_path / "bin"
    shim.mkdir()
    (shim / "dpkg-deb").write_text(
        '#!/bin/sh\nstage="$3"; out="$4"\ncd "$stage" && find . -type f -printf "%m %p\n" | sort > "$out"\n', encoding="utf-8")
    (shim / "dpkg-deb").chmod(0o755)
    out = tmp_path / "out"
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}"}
    # hscl-security has a data file, a shell script and maintainer scripts; make the checkout look like NTFS first
    pkg = ROOT / "packages/debian/hscl-security"
    for p in pkg.rglob("*"):
        if p.is_file():
            p.chmod(0o777)
    try:
        r = subprocess.run(["bash", str(ROOT / "scripts/build-deb.sh"), "hscl-security", str(out)], capture_output=True, text=True, env=env)
    finally:
        for p in pkg.rglob("*"):
            if p.is_file():
                p.chmod(0o644)
    assert r.returncode == 0, r.stderr
    listing = Path(r.stdout.strip().splitlines()[-1]).read_text(encoding="utf-8").splitlines()
    modes = {line.split(" ", 1)[1]: int(line.split(" ", 1)[0], 8) for line in listing}
    assert modes, "no files staged"
    for path, mode in modes.items():
        assert not mode & (stat.S_IWGRP | stat.S_IWOTH), f"{path} is group/world-writable ({oct(mode)})"
    assert modes["./etc/sysctl.d/90-hscl.conf"] == 0o644
    assert modes["./usr/lib/hscl/security-baseline.sh"] == 0o755
