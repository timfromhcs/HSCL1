"""security-baseline.sh calls ufw in a safe order and never touches other protections."""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "distro/security/security-baseline.sh"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs a POSIX shell")


def test_ufw_defaults_before_enable_and_marker_written(tmp_path):
    log = tmp_path / "calls.log"
    fake = tmp_path / "ufw"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{log.as_posix()}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "UFW": fake.as_posix(), "HSCL_STATE_DIR": (tmp_path / "state").as_posix()}
    r = subprocess.run([BASH, str(SCRIPT)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert log.read_text().splitlines() == ["default deny incoming", "default allow outgoing", "--force enable"]
    assert (tmp_path / "state" / "security-baseline.done").exists()


def test_script_does_not_touch_other_protections():
    text = " ".join(l for l in SCRIPT.read_text().splitlines() if not l.lstrip().startswith("#"))
    for forbidden in ("apparmor", "aa-teardown", "setenforce", "secureboot", "mokutil", "sysctl -w", "iptables -F"):
        assert forbidden not in text.lower()


def test_service_is_conditional_and_hardened():
    unit = (ROOT / "distro/security/systemd/hscl-security-baseline.service").read_text()
    assert "ConditionPathExists=!/var/lib/hscl/security-baseline.done" in unit
    assert "NoNewPrivileges=yes" in unit and "Type=oneshot" in unit
