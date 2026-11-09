"""Calamares branding descriptor: window policy and HCS palette.

Visual QA 2026-11-09 (`docs/img/showcase/11_installer_welcome.png`): with `windowExpanding: fullscreen`
the 36 px Plasma top bar was drawn over the installer's branding sidebar and clipped the HSCL1 logo.
Calamares supports only `normal`, `noexpand` and `fullscreen` (no `maximize`), so the installer runs as
a centred window that stays clear of the bar and the dock.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / "packages/debian/hscl-branding/etc/calamares/branding/hscl1/branding.desc"


def load() -> dict:
    text = BRANDING.read_text(encoding="utf-8")
    assert text.startswith("---"), "branding.desc must start with a YAML document marker"
    return yaml.safe_load(text.split("---", 1)[1])


def test_window_is_not_fullscreen_so_the_top_bar_cannot_clip_it():
    data = load()
    assert data["windowExpanding"] in {"normal", "noexpand"}, data["windowExpanding"]
    assert data["windowPlacement"] == "center"


def test_window_size_fits_the_smallest_supported_screen():
    """1366x768 is the smallest layout we support (AGENTS.md 4.1): leave room for the 36 px bar and
    the ~50 px dock."""
    data = load()
    width, height = (int(part.strip().removesuffix("px")) for part in data["windowSize"].split(","))
    assert 900 <= width <= 1280, width
    assert 560 <= height <= 768 - 36 - 50, height


def test_branding_uses_the_hcs_palette():
    style = load()["style"]
    assert style["SidebarBackground"].lower() == "#151a23"
    assert style["SidebarText"].lower() == "#e8ecf3"
    assert style["SidebarTextCurrent"].lower() == "#6c8cff"


def test_product_strings_match_the_version_file():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    data = load()
    assert data["strings"]["version"] == version, (data["strings"]["version"], version)


def test_no_short_version_string_is_truncated():
    """The requirements screen said "installing HSCL1 0.1." because shortVersionedName was "HSCL1 0.1".
    Every version-bearing string must carry the full version."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    strings = load()["strings"]
    for key in ("shortVersion", "versionedName", "shortVersionedName"):
        assert version in strings[key], (key, strings[key], version)
