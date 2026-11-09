"""The palette hook works on the real base files, not only on the idealised one.

Build attempt 1 (2026-11-09) failed because the Kubuntu default kdeglobals has `[General]` but no
`ColorScheme` key, and attempt 2 failed because `/etc/skel/.config/kdeglobals` does not exist in the
base image at all. Both cases are reproduced here in a throwaway rootfs, without building an image.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "scripts/dev/sandbox_hook_check.sh"
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_hook_creates_the_palette_key_in_both_places():
    r = shellutil.run_script(SANDBOX)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sandbox result: PASS" in r.stdout
    assert "ColorScheme=HCSMidnight" in r.stdout


def test_sandbox_covers_the_two_real_failure_modes():
    text = SANDBOX.read_text(encoding="utf-8")
    assert "org.kubuntu.desktop" in text, "case 1: no ColorScheme key in the Kubuntu default"
    assert "/etc/skel/.config/kdeglobals" in text, "case 2: skel file must be created"


def test_hook_creates_the_skel_directory_before_writing():
    text = HOOK.read_text(encoding="utf-8")
    assert 'mkdir -p "$(dirname "$skel_kdeglobals")"' in text
    assert '[ -f "$skel_kdeglobals" ] || : > "$skel_kdeglobals"' in text
