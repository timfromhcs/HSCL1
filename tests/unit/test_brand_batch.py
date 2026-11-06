"""Visible-branding fixes found by the content scan of the 0.1.2-alpha.0 candidate (hook edits and their image gates must stay paired)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")


def test_installer_has_no_upstream_donate_link():
    assert "showDonateUrl: false" in HOOK
    assert "installer: no upstream donate link" in GATE


def test_upstream_website_launchers_are_removed_from_the_menu():
    for name in ("org.kubuntu.web.home.desktop", "org.kfocus.web.howtos.desktop"):
        assert name in HOOK and name in GATE


def test_live_user_and_host_are_set_explicitly_with_flavour():
    # casper honours USERNAME/HOST only when FLAVOUR is set; all three must be patched together
    for needle in ('export USERNAME="hscl1"', 'export HOST="hscl1"', 'export FLAVOUR="HSCL1"'):
        assert needle in HOOK, needle
    for needle in ("live user is hscl1", "live host is hscl1", "casper FLAVOUR set"):
        assert needle in GATE, needle


def test_plymouth_animation_does_not_overlap_the_message_line():
    gen = (ROOT / "scripts/gen_plymouth.py").read_text(encoding="utf-8")
    assert "\nVerticalAlignment=.58\n" in gen
