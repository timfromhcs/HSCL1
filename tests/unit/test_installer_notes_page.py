"""Installer 'Notes' page about disk encryption (AGENTS.md 6.3): source, translations, hook and image gates stay paired.

Why qsTr + .qm: on the dev2 image the UI language switched to German but `Qt.locale().name` stayed `en_US`, so a page choosing text by locale
stayed English (seen on screen 2026-11-07). Calamares loads branding translations from lang/calamares-<component>_<lang>.qm.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "packages/debian/hscl-branding"
QML = BRAND / "etc/calamares/branding/hscl1/notesqml.qml"
I18N = ROOT / "distro/installer/i18n"
HOOK = (ROOT / "distro/live/hooks/010-hscl-defaults.sh").read_text(encoding="utf-8")
GATE = (ROOT / "distro/live/verify-image.sh").read_text(encoding="utf-8")
BUILD = (BRAND / "build.sh").read_text(encoding="utf-8")


def qml_sources():
    text = QML.read_text(encoding="utf-8")
    found = re.findall(r'qsTr\("((?:[^"\\]|\\.)*)"\)', text)
    return [s.replace('\\"', '"') for s in found], text


def ts_messages(lang):
    root = ET.parse(I18N / f"calamares-hscl1_{lang}.ts").getroot()
    assert root.get("language") == lang
    ctx = {c.findtext("name"): c for c in root.findall("context")}
    assert "notesqml" in ctx, "QML context name is the file base name"
    out = {}
    for m in ctx["notesqml"].findall("message"):
        tr = m.find("translation")
        out[m.findtext("source")] = (tr.text or "", tr.get("type"))
    return out


def test_page_uses_qsTr_and_not_the_locale_name():
    sources, text = qml_sources()
    assert len(sources) >= 6, sources
    assert "Qt.locale().name" not in text  # does not follow the installer language (seen on screen)
    assert not re.search(r"\bDEBUG\b", text)


def test_every_source_string_has_a_finished_german_and_french_translation():
    sources, _ = qml_sources()
    for lang in ("de", "fr"):
        msgs = ts_messages(lang)
        for s in sources:
            assert s in msgs, f"{lang}: missing {s[:50]!r}"
            text, kind = msgs[s]
            assert text.strip() and kind not in ("unfinished", "vanished", "obsolete"), f"{lang}: {s[:50]!r}"
            assert text != s, f"{lang}: untranslated {s[:50]!r}"


def test_no_stale_translations():
    sources, _ = qml_sources()
    for lang in ("de", "fr"):
        assert set(ts_messages(lang)) <= set(sources), lang


def test_the_honest_statements_are_in_the_source_text():
    sources, _ = qml_sources()
    joined = " ".join(sources)
    assert "no recovery key" in joined          # only one keyslot exists (BUILD_LOG, LUKS offline inspection)
    assert "/boot" in joined and "EFI" in joined
    assert "off unless" in joined               # encryption is not the default
    assert "does not replace backups" in joined


def test_package_build_compiles_the_translations_and_fails_without_the_tool():
    assert "lrelease" in BUILD and "calamares-hscl1_" in BUILD
    assert "etc/calamares/branding/hscl1/lang" in BUILD
    assert re.search(r"lrelease[^\n]*\n[^\n]*(exit 1|return 1)|missing[^\n]*lrelease|lrelease[^\n]*not found", BUILD), "must fail loudly when lrelease is missing"


def test_hook_adds_the_page_before_partition_and_its_config():
    assert "notesqml" in HOOK and "modules/notesqml.conf" in HOOK
    assert "qmlSearch: branding" in HOOK
    assert re.search(r"settings\.conf", HOOK) and "partition" in HOOK


def test_image_gates_check_page_translations_config_and_order():
    for name in ("installer notes page installed", "installer notes: German and French translations",
                 "installer notes: module config", "installer notes: shown before partition"):
        assert name in GATE, name
    assert "calamares-hscl1_de.qm" in GATE and "calamares-hscl1_fr.qm" in GATE
