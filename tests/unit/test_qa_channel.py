"""hscl-qa: inert without the virtio port, writes a well-formed report with it, never writes outside QA_OUT."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "packages/debian/hscl-qa/usr/lib/hscl/qa/run.sh"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs a POSIX shell")


def run(out, **env):
    e = {**os.environ, "QA_WAIT": "0", "QA_SETTLE": "0", "QA_OUT": out.as_posix(), **env}
    return subprocess.run([BASH, str(RUN)], capture_output=True, text=True, env=e)


def test_inert_when_port_missing(tmp_path):
    r = run(tmp_path / "missing" / "hscl.qa")
    assert r.returncode == 0
    assert not (tmp_path / "missing").exists()


def test_report_sections_when_port_exists(tmp_path):
    out = tmp_path / "hscl.qa"
    out.write_text("")
    assert run(out).returncode == 0
    text = out.read_text()
    for name in ("hscl-qa", "os-release", "hscl-status", "hscl-doctor", "secure-boot", "apparmor", "ufw", "listening", "failed-units", "sysctl", "end"):
        assert f"== {name} ==" in text, name
    assert text.rstrip().endswith("== end ==")


def test_script_is_read_only_by_inspection():
    body = "\n".join(l for l in RUN.read_text().splitlines() if not l.lstrip().startswith("#"))
    for forbidden in ("rm ", "mkfs", "dd ", "systemctl stop", "systemctl disable", "ufw disable", "aa-teardown", "apt "):
        assert forbidden not in body, forbidden


def test_service_is_conditional_on_the_port():
    unit = (ROOT / "packages/debian/hscl-qa/usr/lib/systemd/system/hscl-qa.service").read_text()
    assert "ConditionPathExists=/dev/virtio-ports/hscl.qa" in unit
