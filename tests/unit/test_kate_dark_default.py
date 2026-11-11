"""Kate should open dark on a dark desktop.

Measured 2026-11-10 (Q-53): `docs/img/showcase/14_app_kate.png` shows a light Kate window and menu bar inside the
HCS dark shell, while Dolphin and Konsole are dark. Kate does not follow the Plasma palette by itself - the
application chrome uses `[UiSettings] ColorScheme` and the editor area uses the KSyntaxHighlighting
`[KTextEditor Renderer] Color Theme`, so the hook ships an explicit Breeze Dark default for new users.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"


def test_the_hook_ships_a_dark_kate_default():
    text = HOOK.read_text(encoding="utf-8")
    assert 'cat > "$ROOTFS/etc/skel/.config/katerc"' in text
    assert "ColorScheme=Breeze Dark" in text, "Kate's window chrome would stay light"
    assert "Color Theme=Breeze Dark" in text, "the editor area would stay light"
    assert "Auto Color Theme Selection=false" in text, "auto selection can override the pinned theme"


def test_the_reason_is_documented():
    text = HOOK.read_text(encoding="utf-8")
    assert "Q-53" in text
