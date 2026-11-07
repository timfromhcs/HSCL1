"""security-baseline.sh calls ufw in a safe order and never touches other protections."""
import stat
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "distro/security/security-baseline.sh"
pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


def test_ufw_defaults_before_enable_and_marker_written(tmp_path):
    log = tmp_path / "calls.log"
    fake = tmp_path / "ufw"
    fake.write_bytes(f'#!/bin/sh\necho "$@" >> "{shellutil.to_bash_path(log)}"\n'.encode())
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    r = shellutil.run_script(
        SCRIPT,
        env_overrides={"UFW": fake, "HSCL_STATE_DIR": tmp_path / "state"},
    )
    assert r.returncode == 0, r.stderr
    assert log.read_text().splitlines() == ["default deny incoming", "default allow outgoing", "--force enable"]
    assert (tmp_path / "state" / "security-baseline.done").exists()


def test_script_does_not_touch_other_protections():
    text = " ".join(line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("apparmor", "aa-teardown", "setenforce", "secureboot", "mokutil", "sysctl -w", "iptables -F"):
        assert forbidden not in text.lower()


def test_service_is_conditional_and_hardened():
    unit = (ROOT / "distro/security/systemd/hscl-security-baseline.service").read_text()
    assert "ConditionPathExists=!/var/lib/hscl/security-baseline.done" in unit
    assert "NoNewPrivileges=yes" in unit and "Type=oneshot" in unit
