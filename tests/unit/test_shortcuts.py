"""HSCL1 Keyboard Shortcuts: configuration, look-and-feel defaults, helper script, and documentation parity (AGENTS.md 4.5)."""
import configparser
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages/debian/hscl-desktop"
KSHORTCUTS = PKG / "etc/xdg/kglobalshortcutsrc"
DEFAULTS = PKG / "usr/share/plasma/look-and-feel/org.hcs.hscl1.desktop/contents/defaults"
DOC = ROOT / "docs/SHORTCUTS.md"
DESKTOP_ENTRY = PKG / "usr/share/applications/hscl-shortcuts.desktop"
HELPER_BIN = PKG / "usr/bin/hscl-shortcuts"

REQUIRED_SHORTCUTS = [
    ("Meta + Space", "org.kde.krunner.desktop", "_launch"),
    ("Meta + Enter", "org.kde.konsole.desktop", "_launch"),
    ("Ctrl + Alt + T", "org.kde.konsole.desktop", "_launch"),
    ("Meta + E", "org.kde.dolphin.desktop", "_launch"),
    ("Meta + D", "kwin", "Show Desktop"),
    ("Meta + Tab", "kwin", "Walk Through Windows"),
    ("Meta + K", "hscl-shortcuts.desktop", "_launch"),
    ("Meta + ,", "hscl-control-center.desktop", "_launch"),
    ("Meta + L", "ksmserver", "Lock Session"),
    ("Meta + Shift + S", "org.kde.spectacle.desktop", "RectangularRegionScreenShot"),
    ("Meta + Left", "kwin", "Window Quick Tile Left"),
    ("Meta + Right", "kwin", "Window Quick Tile Right"),
    ("Meta + Up", "kwin", "Window Maximize"),
    ("Meta + Down", "kwin", "Window Minimize"),
    ("Meta + 1", "kwin", "Switch to Desktop 1"),
    ("Meta + 2", "kwin", "Switch to Desktop 2"),
    ("Meta + 3", "kwin", "Switch to Desktop 3"),
    ("Meta + 4", "kwin", "Switch to Desktop 4"),
    ("Meta + 5", "kwin", "Switch to Desktop 5"),
    ("Meta + 6", "kwin", "Switch to Desktop 6"),
    ("Meta + 7", "kwin", "Switch to Desktop 7"),
    ("Meta + 8", "kwin", "Switch to Desktop 8"),
    ("Meta + 9", "kwin", "Switch to Desktop 9"),
]


def test_kglobalshortcutsrc_exists_and_is_valid_ini():
    assert KSHORTCUTS.is_file(), f"missing {KSHORTCUTS}"
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(KSHORTCUTS, encoding="utf-8")
    assert "kwin" in cfg.sections()
    assert "org.kde.konsole.desktop" in cfg.sections()
    assert "org.kde.dolphin.desktop" in cfg.sections()
    assert "hscl-shortcuts.desktop" in cfg.sections()
    assert "hscl-control-center.desktop" in cfg.sections()


def test_all_agents_required_shortcuts_are_configured():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(KSHORTCUTS, encoding="utf-8")

    key_aliases = {
        "Meta + Enter": "Meta+Return",
        "Meta + Space": "Meta+Space",
        "Ctrl + Alt + T": "Ctrl+Alt+T",
        "Meta + E": "Meta+E",
        "Meta + D": "Meta+D",
        "Meta + Tab": "Meta+Tab",
        "Meta + K": "Meta+K",
        "Meta + ,": "Meta+,",
        "Meta + L": "Meta+L",
        "Meta + Shift + S": "Meta+Shift+S",
        "Meta + Left": "Meta+Left",
        "Meta + Right": "Meta+Right",
        "Meta + Up": "Meta+Up",
        "Meta + Down": "Meta+Down",
        "Meta + 1": "Meta+1",
        "Meta + 2": "Meta+2",
        "Meta + 3": "Meta+3",
        "Meta + 4": "Meta+4",
        "Meta + 5": "Meta+5",
        "Meta + 6": "Meta+6",
        "Meta + 7": "Meta+7",
        "Meta + 8": "Meta+8",
        "Meta + 9": "Meta+9",
    }

    for name, section, key in REQUIRED_SHORTCUTS:
        assert section in cfg, f"missing section [{section}] for {name}"
        assert key in cfg[section], f"missing key {key} in [{section}] for {name}"
        raw_val = cfg[section][key]
        expected_token = key_aliases[name]
        assert expected_token in raw_val, f"expected shortcut token '{expected_token}' not in '{raw_val}' for {name}"


def test_look_and_feel_defaults_contain_shortcuts():
    text = DEFAULTS.read_text(encoding="utf-8")
    for _, section, key in REQUIRED_SHORTCUTS:
        pattern = rf"\[kglobalshortcutsrc\]\[{re.escape(section)}\]"
        assert re.search(pattern, text), f"missing look-and-feel group [kglobalshortcutsrc][{section}]"
        assert f"{key}=" in text, f"missing look-and-feel entry for {key} in defaults"


def test_no_shortcut_conflicts_in_configuration():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(KSHORTCUTS, encoding="utf-8")

    seen_triggers = {}
    for sec in cfg.sections():
        for k, v in cfg[sec].items():
            if k.startswith("_k_"):
                continue
            # First field before comma is the active shortcut (may have secondary after \t)
            active_field = v.split(",")[0] if "," in v else v
            for trigger in active_field.split(r"\t"):
                t = trigger.strip()
                if not t or t.lower() == "none":
                    continue
                # Same trigger cannot be mapped to two distinct actions
                assert t not in seen_triggers, f"conflicting shortcut {t}: {seen_triggers[t]} vs ({sec}, {k})"
                seen_triggers[t] = (sec, k)


def test_shortcuts_doc_covers_all_bound_shortcuts():
    doc_text = DOC.read_text(encoding="utf-8")
    assert "HSCL1 Keyboard Shortcuts Reference" in doc_text
    assert "Made with love by hcsmedia" in doc_text

    for name, _, _ in REQUIRED_SHORTCUTS:
        assert f"`{name}`" in doc_text, f"shortcut {name} not documented in {DOC}"


def test_helper_binary_and_desktop_entry_exist():
    assert HELPER_BIN.is_file(), f"missing {HELPER_BIN}"
    assert DESKTOP_ENTRY.is_file(), f"missing {DESKTOP_ENTRY}"

    desktop_text = DESKTOP_ENTRY.read_text(encoding="utf-8")
    assert "Type=Application" in desktop_text
    assert "Exec=hscl-shortcuts" in desktop_text
    assert "Name[de]=" in desktop_text
    assert "Name[fr]=" in desktop_text

    bin_text = HELPER_BIN.read_text(encoding="utf-8")
    assert "#!/bin/sh" in bin_text
    assert "hscl-handbook" in bin_text
    assert "Made with love by hcsmedia" in bin_text


def test_handbook_desktop_page_contains_shortcut_table():
    for lang in ("en", "de", "fr"):
        page = ROOT / f"handbook/{lang}/src/desktop.md"
        assert page.is_file()
        text = page.read_text(encoding="utf-8")
        assert "Meta + Space" in text or "Meta + Leertaste" in text or "Meta + Espace" in text
        assert "Meta + Enter" in text or "Meta + Eingabetaste" in text or "Meta + Entrée" in text
        assert "Ctrl + Alt + T" in text
        assert "Meta + K" in text
