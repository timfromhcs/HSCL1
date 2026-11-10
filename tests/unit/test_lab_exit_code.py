"""`hscl lab` must pass the container's exit code through to the caller.

The bug sat in the caller, not in `lab_execute` (that function always returned the code): `run_lab` discarded
the result and returned `exit::OK`, so a failed container still looked like success. Measured in the live guest
on 2026-11-10: `lab action finished: project=demo exit=125` followed by shell `INSTALL_EXIT=0`, because podman
refused an image that had not been pulled.

This test drives the real CLI with a `podman` shim that exits 42, so it fails if the code is dropped again.
It needs a POSIX shell for the shim; the WSL pytest gate covers that, Windows skips it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALID_IMAGE = "docker.io/kalilinux/kali-rolling@sha256:" + "a" * 64
ATTESTATION = "I am authorized to test this target"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="needs a POSIX shell for the podman shim (the WSL gate runs it)")


def _hscl() -> str:
    """A binary that is at least as new as the sources; otherwise skip instead of testing stale code."""
    exe = ROOT / "target" / "debug" / "hscl"
    newest_src = max((p.stat().st_mtime for p in (ROOT / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0)
    if exe.is_file() and exe.stat().st_mtime >= newest_src:
        return str(exe)
    which = shutil.which("hscl")
    if which and Path(which).stat().st_mtime >= newest_src:
        return which
    pytest.skip("hscl binary is older than the sources (rebuild before running this test)")


def _run(tmp_path: Path, exit_code: int) -> subprocess.CompletedProcess[str]:
    shim = tmp_path / "podman"
    shim.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    shim.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"}
    return subprocess.run(
        [
            _hscl(), "lab", "run", "--project", "demo", "--image", VALID_IMAGE,
            # clap declares `--yes[=<YES>]`, so the value must be attached with `=`.
            f"--yes={ATTESTATION}", "--", "true",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(ROOT), check=False, timeout=120,
    )


def test_a_failing_container_exit_code_reaches_the_caller(tmp_path: Path):
    res = _run(tmp_path, 42)
    assert res.returncode == 42, (res.returncode, res.stdout[-300:], res.stderr[-300:])
    assert "exit=42" in res.stdout


def test_a_succeeding_container_still_returns_zero(tmp_path: Path):
    res = _run(tmp_path, 0)
    assert res.returncode == 0, (res.returncode, res.stdout[-300:], res.stderr[-300:])
