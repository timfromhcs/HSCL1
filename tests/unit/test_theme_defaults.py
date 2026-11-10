"""The HCS palette must be the default for widget apps, not only for the Plasma shell.

Visual QA of the 2026-11-09 candidate screenshots: the shell (top bar, dock, Control Center) was dark,
but Dolphin and Konsole content were light Breeze. The hook therefore has to set `ColorScheme` in the
settings that new users inherit, and the image gate has to prove it. The scheme name is derived from
the design tokens so a rename cannot silently desynchronise the three places.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")
GEN = (ROOT / "scripts/gen_colorschemes.py").read_text(encoding="utf-8")


def midnight_scheme_name() -> str:
    tokens = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
    assert "hcs-midnight" in tokens["themes"], tokens["themes"].keys()
    # mirrors scheme_name() in gen_colorschemes.py: "HCS" + capitalised suffix
    return "HCS" + "hcs-midnight"[len("hcs-") :].capitalize()


def test_scheme_name_helper_matches_the_generator():
    assert '"HCS" + theme_id[len("hcs-"):].capitalize()' in GEN
    assert midnight_scheme_name() == "HCSMidnight"


def test_hook_makes_the_hcs_palette_the_default():
    name = midnight_scheme_name()
    # ensure_key, not sed: the Kubuntu default file has [General] but no ColorScheme key at all.
    assert f"General ColorScheme {name}" in HOOK, "the hook must set the palette for new users"
    assert "kubuntu-default-settings/kf5-settings/kdeglobals" in HOOK
    assert "/etc/skel/.config/kdeglobals" in HOOK, "live users come from /etc/skel"


def test_image_gate_proves_the_palette_is_the_default():
    name = midnight_scheme_name()
    assert f"ColorScheme={name}" in GATE, "verify-image.sh must check the shipped default"
    assert f"/usr/share/color-schemes/{name}.colors" in GATE
    assert "/etc/skel/.config/kdeglobals" in GATE


def test_look_and_feel_defaults_also_name_the_palette():
    lnf = ROOT / "packages/debian/hscl-desktop/usr/share/plasma/look-and-feel/org.hcs.hscl1.desktop/contents/defaults"
    text = lnf.read_text(encoding="utf-8")
    assert re.search(r"^ColorScheme=HCS\w+M?$", text, re.MULTILINE), text
    assert re.search(r"^widgetStyle=\S+$", text, re.MULTILINE), text


def test_dark_icon_theme_is_selected():
    lnf = ROOT / "packages/debian/hscl-desktop/usr/share/plasma/look-and-feel/org.hcs.hscl1.desktop/contents/defaults"
    assert "Theme=breeze-dark" in lnf.read_text(encoding="utf-8")


def test_desktop_icon_font_is_pinned_upright():
    """Visual audit 2026-11-10: every capture showed oblique (italic) desktop icon labels.

    The desktop font is pinned in /etc/skel so no vendor look-and-feel can leave it oblique, and the
    image gate rejects an italic value. Horizontal alignment is upstream FolderView behaviour and is
    still verified by a booted capture (Q-52), not by this test.
    """
    assert re.search(r'^ensure_key "\$skel_kdeglobals" Fonts desktopFont "Noto Sans,[\d,-]+"$', HOOK, re.MULTILINE), (
        "the hook must pin an upright desktop font"
    )
    assert "desktopFont=.*Italic" in GATE, "verify-image.sh must reject an oblique desktop font"
