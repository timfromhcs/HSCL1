"""The earlyoom policy must not sacrifice the installer or the desktop shell.

Measured 2026-11-09: at 4 GB `sudo calamares -d` printed `Killed` / `EXIT=137` and drkonqi died with it,
while the same image installed normally at 6 GB. earlyoom picked the largest new process because
Calamares was not in the avoid list. This test pins the policy that fixes it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DROPIN = ROOT / "packages/debian/hscl-memory/etc/systemd/system/earlyoom.service.d/90-hscl.conf"
GATE = ROOT / "distro/live/verify-image.sh"


def avoid_list() -> str:
    text = DROPIN.read_text(encoding="utf-8")
    match = re.search(r"--avoid '([^']+)'", text)
    assert match, "no --avoid expression"
    return match.group(1)


def test_the_installer_is_never_the_victim():
    avoid = avoid_list()
    for name in ("calamares", "drkonqi"):
        assert re.search(rf"\b{name}\b", avoid), (name, avoid)


def test_the_desktop_shell_stays_protected():
    avoid = avoid_list()
    for name in ("plasmashell", "kwin_wayland", "sddm"):
        assert name in avoid, (name, avoid)


def test_real_memory_hogs_are_still_preferred():
    text = DROPIN.read_text(encoding="utf-8")
    match = re.search(r"--prefer '([^']+)'", text)
    assert match, "no --prefer expression"
    assert "llama-server" in match.group(1)


def test_the_image_gate_checks_the_installer_exemption():
    assert "calamares" in GATE.read_text(encoding="utf-8")
