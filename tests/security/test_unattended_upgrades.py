"""Unattended upgrades: security pocket only, no reboot, list cleared before our origin is added."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONF = (ROOT / "distro/security/apt/52hscl-unattended-upgrades").read_text(encoding="utf-8")


def active():
    return "\n".join(l for l in CONF.splitlines() if not l.strip().startswith("//"))


def test_only_security_origin_is_allowed():
    origins = re.findall(r'"(\$\{distro_id\}:[^"]+)";', active())
    assert origins == ["${distro_id}:${distro_codename}-security"]
    for bad in ("-updates", "-proposed", "-backports", "ESM"):
        assert bad not in active()


def test_list_is_cleared_before_it_is_set():
    a = active()
    assert a.index("#clear Unattended-Upgrade::Allowed-Origins") < a.index("Unattended-Upgrade::Allowed-Origins {")


def test_no_automatic_reboot_and_no_dependency_removal():
    assert 'Unattended-Upgrade::Automatic-Reboot "false";' in active()
    assert 'Unattended-Upgrade::Remove-Unused-Dependencies "false";' in active()
    assert 'Unattended-Upgrade "1"' in active()
