"""Calamares branding for HSCL1: required keys, no Kubuntu leftovers, slideshow in en/de/fr."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BR = ROOT / "packages/debian/hscl-branding/etc/calamares/branding/hscl1"


def desc():
    out = {}
    for line in (BR / "branding.desc").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s+(\w+):\s+(.+)", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def test_required_strings_and_names():
    d = desc()
    for key in ("productName", "shortProductName", "version", "versionedName", "bootloaderEntryName", "productLogo", "productIcon", "productWelcome", "SidebarBackground"):
        assert key in d, key
    assert d["productName"] == "HSCL1" and d["bootloaderEntryName"] == "HSCL1"
    assert "componentName: hscl1" in (BR / "branding.desc").read_text(encoding="utf-8")


def test_no_kubuntu_or_kfocus_leftovers():
    for f in BR.iterdir():
        assert "kubuntu" not in f.read_text(encoding="utf-8").lower(), f.name
        assert "kfocus" not in f.read_text(encoding="utf-8").lower(), f.name


def test_slideshow_has_three_languages():
    qml = (BR / "show.qml").read_text(encoding="utf-8")
    assert qml.count("Slide {") == 3
    assert "Mit Liebe gemacht von hcsmedia" in qml and "Fait avec amour par hcsmedia" in qml
    assert "Meta+K" not in qml, "do not advertise shortcuts that are not bound"
    assert "Handbook" in qml and "Handbuch" in qml and "manuel" in qml


def test_installer_version_matches_the_VERSION_file():
    """Found 2026-11-07 in the live installer of the 0.1.3-alpha.0 ISO: the title read 'HSCL1 0.1.2-alpha.0 installer' because
    branding.desc was not bumped with VERSION."""
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    d = desc()
    assert d["version"] == v
    assert d["versionedName"] == f"HSCL1 {v}"
