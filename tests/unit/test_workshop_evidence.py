"""hscl-workshop: inert without the virtio port, writes a well-formed report with it, never writes outside QA_OUT."""
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "packages/debian/hscl-workshop/usr/lib/hscl/workshop/evidence.sh"
pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


def run(out, **env):
    return shellutil.run_script(
        RUN,
        env_overrides={"QA_WAIT": "0", "QA_SETTLE": "0", "QA_OUT": out, **env},
    )


def test_inert_when_port_missing(tmp_path):
    r = run(tmp_path / "missing" / "hscl.qa")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "missing").exists()


def test_report_sections_when_port_exists(tmp_path):
    out = tmp_path / "hscl.qa"
    out.write_text("")
    r = run(out)
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8", errors="replace")
    for name in ("hscl-qa", "os-release", "hscl-status", "hscl-doctor", "secure-boot", "apparmor", "ufw", "listening", "failed-units", "sysctl", "look-and-feel-packages", "system-lookandfeel", "skel-lookandfeel", "end"):
        assert f"== {name} ==" in text, name
    assert text.rstrip().endswith("== end ==")


def test_script_is_read_only_by_inspection():
    body = "\n".join(line for line in RUN.read_text().splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("rm ", "mkfs", "dd ", "systemctl stop", "systemctl disable", "ufw disable", "aa-teardown", "apt "):
        assert forbidden not in body, forbidden


def test_service_is_conditional_on_the_port():
    unit = (ROOT / "packages/debian/hscl-workshop/usr/lib/systemd/system/hscl-workshop-evidence.service").read_text()
    assert "ConditionPathExists=/dev/virtio-ports/hscl.qa" in unit


def test_workshop_is_inert_by_design():
    base = ROOT / "packages/debian/hscl-workshop"
    unit = (base / "usr/lib/systemd/system/hscl-workshop-evidence.service").read_text()
    assert "[Install]" not in unit, "no enable symlinks: udev starts the unit"
    rules = (base / "usr/lib/udev/rules.d/90-hscl-workshop.rules").read_text()
    assert 'ATTR{name}=="hscl.qa"' in rules and 'ATTR{name}=="hscl.api"' in rules
    assert "ListenStream" not in unit
    assert not list(base.rglob("*.socket")), "no socket units (no network listener)"
