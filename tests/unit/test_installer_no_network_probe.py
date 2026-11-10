"""The installer must not probe the network at startup.

Measured 2026-11-10: `KCrash: Application 'calamares' crashing... crashRecursionCounter = 2` appeared right
after `CalamaresApplication::initViewSteps()` / `ModuleManager::checkRequirements()`, and Calamares was then
SIGKILLed (status 137). The welcome module's `internet` check performs an HTTPS request in exactly that phase.
The image installs offline, so the probe is removed and an image gate keeps it removed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_hook_removes_the_internet_check():
    text = HOOK.read_text(encoding="utf-8")
    assert re.search(r"modules/welcome\.conf\"\s+'/\^\\s*- internet\$?/d'", text) or "/^        - internet$/d" in text, (
        "the hook must delete the internet entry from welcome.conf"
    )
    assert "welcome.conf" in text


def test_the_image_gate_checks_it():
    text = GATE.read_text(encoding="utf-8")
    assert "installer: no internet requirement" in text
    assert "- internet" in text


def test_the_checks_that_stay_are_documented():
    """storage, ram, power and root remain - dropping every check would hide real blockers."""
    text = HOOK.read_text(encoding="utf-8")
    assert "storage/ram/power/root" in text
