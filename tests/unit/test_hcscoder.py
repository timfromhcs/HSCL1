"""hcscoder launcher: runs setup quietly, then launches with the user's arguments after `--`."""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "packages/debian/hscl-base/usr/bin/hcscoder"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs a POSIX shell")


def test_launcher_calls_setup_then_launch_with_arguments(tmp_path):
    log = tmp_path / "calls.log"
    fake = tmp_path / "hscl"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{log.as_posix()}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{tmp_path.as_posix()}{os.pathsep}{os.environ['PATH']}"}
    r = subprocess.run([BASH, str(LAUNCHER), "--model", "x", "fix the bug"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert log.read_text().splitlines() == ["code setup", "code launch -- --model x fix the bug"]


def test_desktop_entry_credits_upstream_and_runs_in_a_terminal():
    d = (ROOT / "packages/debian/hscl-base/usr/share/applications/hcscoder.desktop").read_text(encoding="utf-8")
    assert "Terminal=true" in d and "OpenCode" in d and "Exec=hcscoder" in d
