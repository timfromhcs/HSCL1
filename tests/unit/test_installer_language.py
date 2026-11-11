"""The installer must not open in an arbitrary language.

Seen on rc11 (2026-11-11): the live session runs with `LANG=C.UTF-8`, so Calamares has no usable system
locale and picked the first available translation alphabetically - Azerbaijani ("Xoş Gəldiniz",
"Bölmələr", "Quraşdırmaq"). HSCL1 ships en/de/fr; the welcome page must start in English and let the
user switch.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")


def test_the_hook_pins_the_installer_language():
    assert 'welcome.conf" \'s/^\\(\\s*\\)language:.*/\\1language: "en"/\'' in HOOK, (
        "welcome.conf must pin language: \"en\""
    )


def test_the_hook_gives_the_live_session_a_locale():
    assert 'LANG="en_US.UTF-8"' in HOOK
    assert "etc/default/locale" in HOOK


def test_the_image_gate_checks_both():
    assert 'installer language is pinned to English' in GATE
    assert 'live locale is set' in GATE


def test_the_reason_is_documented_next_to_the_fix():
    assert "az" in HOOK.lower() or "azerbaijan" in HOOK.lower(), (
        "the measured symptom must stay next to the fix"
    )
