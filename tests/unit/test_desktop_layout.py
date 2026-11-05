"""HCS Hybrid Desktop package: metadata, defaults, and layout scripts reference real widget ids only."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages/debian/hscl-desktop/usr/share/plasma"
KNOWN_WIDGETS = {
    "org.kde.plasma.kickoff", "org.kde.plasma.appmenu", "org.kde.plasma.panelspacer", "org.kde.plasma.digitalclock",
    "org.kde.plasma.systemtray", "org.kde.plasma.icontasks", "org.kde.plasma.marginsseparator", "org.kde.plasma.trash",
}


def test_metadata_is_valid_json_with_expected_ids():
    lnf = json.loads((PKG / "look-and-feel/org.hcs.hscl1.desktop/metadata.json").read_text(encoding="utf-8"))
    assert lnf["KPlugin"]["Id"] == "org.hcs.hscl1.desktop"
    assert lnf["KPackageStructure"] == "Plasma/LookAndFeel"
    for tid in ("topbar", "dock"):
        t = json.loads((PKG / f"layout-templates/org.hcs.hscl1.{tid}/metadata.json").read_text(encoding="utf-8"))
        assert t["KPlugin"]["Id"] == f"org.hcs.hscl1.{tid}"


def test_layout_scripts_only_use_known_widgets():
    for js in PKG.rglob("*.js"):
        for wid in re.findall(r"addWidget\('([^']+)'\)", js.read_text(encoding="utf-8")):
            assert wid in KNOWN_WIDGETS, (js.name, wid)


def test_dock_is_floating_centered_and_not_autohiding():
    js = (PKG / "layout-templates/org.hcs.hscl1.dock/contents/layout.js").read_text(encoding="utf-8")
    assert "dock.floating = 1" in js and "dock.alignment = 'center'" in js and "dock.hiding = 'normal'" in js


def test_top_bar_is_slim_and_has_required_parts():
    js = (PKG / "layout-templates/org.hcs.hscl1.topbar/contents/layout.js").read_text(encoding="utf-8")
    assert "bar.location = 'top'" in js and "2 * gridUnit" in js
    for w in ("kickoff", "appmenu", "digitalclock", "systemtray"):
        assert f"org.kde.plasma.{w}" in js


def test_defaults_use_hcs_midnight_and_wallpaper():
    d = (PKG / "look-and-feel/org.hcs.hscl1.desktop/contents/defaults").read_text(encoding="utf-8")
    assert "ColorScheme=HCSMidnight" in d and "Image=HSCL1Midnight" in d
