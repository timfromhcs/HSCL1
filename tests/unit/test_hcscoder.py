"""hcscoder launcher: runs setup quietly, then launches with the user's arguments after `--`."""
import os
import stat
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "packages/debian/hscl-base/usr/bin/hcscoder"
pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


def test_launcher_calls_setup_then_launch_with_arguments(tmp_path):
    log = tmp_path / "calls.log"
    fake = tmp_path / "hscl"
    # the shim writes with the path form of the bash that will run it (native vs WSL)
    fake.write_bytes(f'#!/bin/sh\necho "$@" >> "{shellutil.to_bash_path(log)}"\n'.encode())
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    r = shellutil.run_script(
        LAUNCHER,
        "--model",
        "x",
        "fix the bug",
        env_overrides={"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"},
    )
    assert r.returncode == 0, r.stderr
    assert log.read_text().splitlines() == ["code setup", "code launch -- --model x fix the bug"]


def test_desktop_entry_credits_upstream_and_runs_in_a_terminal():
    d = (ROOT / "packages/debian/hscl-base/usr/share/applications/hcscoder.desktop").read_text(encoding="utf-8")
    assert "Terminal=true" in d and "OpenCode" in d and "Exec=hcscoder" in d
