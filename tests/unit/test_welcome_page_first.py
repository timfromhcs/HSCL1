"""The Welcome Center must open on the HSCL1 page, not on Plasma's built-in KDE page.

Measured 2026-11-11: on rc6/rc7/rc8 the first window of the Welcome Center was "Welcome to the HSCL1 operating
system running KDE Plasma!" with the green Konqi mascot, because `plasma-welcome` shows its built-in pages first
and appends `/usr/share/plasma/plasma-welcome/extra-pages/*.qml` afterwards - our page was simply last.

`plasma-welcome --help` documents `--pages <pages>` ("Specify comma-delimited list of page(s) (by internal name) to
be displayed"), and the internal name turned out to be the file stem in extra-pages: `--pages HSCL1` looked for
`extra-pages/HSCL1.qml` and failed, `--pages 01-HSCL1` opened our page as the only page
(`artifacts/boot-welcome-name/wh3-pages-01-HSCL1.png`). The hook therefore patches the desktop entry.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"
PAGE = ROOT / "packages/debian/hscl-branding/usr/share/plasma/plasma-welcome/extra-pages/01-HSCL1.qml"


def test_the_hook_passes_the_page_name():
    text = HOOK.read_text(encoding="utf-8")
    assert "s/^Exec=plasma-welcome$/Exec=plasma-welcome --pages 01-HSCL1/" in text
    assert "--pages 01-HSCL1" in text


def test_the_page_name_matches_the_installed_file_stem():
    """`--pages X` resolves to `extra-pages/X.qml`; a rename must fail this test, not the guest."""
    assert PAGE.is_file(), "the page file moved; update the --pages argument with it"
    assert PAGE.stem == "01-HSCL1"


def test_the_image_gate_checks_the_desktop_entry():
    text = GATE.read_text(encoding="utf-8")
    assert "Welcome Center opens on the HSCL1 page" in text
    assert "Exec=plasma-welcome --pages 01-HSCL1" in text


def test_the_tour_is_marked_as_seen_for_new_users():
    """Plasma starts the tour itself at the first login, without arguments and without an autostart file.

    Measured 2026-11-11 on an installed rc9 disk: `grep -rl plasma-welcome /etc/xdg/autostart
    /usr/share/applications /home/*/.config` finds only the two desktop files, and the first login showed the KDE
    page with eight dots. Writing `LastSeenVersion` = installed Plasma version into
    `~/.config/plasma-welcomerc` suppressed it (`artifacts/boot-first-login-rc9b/fl1-first-login.png` shows the
    bare desktop). The hook must derive that version from the package, never hardcode it.
    """
    text = HOOK.read_text(encoding="utf-8")
    assert "plasma-welcomerc" in text
    assert "LastSeenVersion" in text
    assert "Package: plasma-workspace" in text, "the version must come from the package, not a literal"
    assert "6.6." not in text.split("plasma_ver=")[1].split("ensure_key")[0], "no hardcoded version"


def test_the_image_gate_checks_the_suppression():
    text = GATE.read_text(encoding="utf-8")
    assert "Welcome Center tour suppressed for new users" in text
    assert "LastSeenVersion=[0-9]+" in text
