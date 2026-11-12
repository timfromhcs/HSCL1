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


def test_the_step_is_no_longer_inserted_into_the_sequence():
    """Q-68: `NotesQmlViewStep::prettyName()` segfaults while the progress tree paints it.

    The hook used to patch the sequence with `- notesqml`. The assets and the module config stay (so the step can be
    re-enabled once upstream makes `prettyName()` safe), but the sequence line must not come back without evidence.
    """
    assert "modules/notesqml.conf" in HOOK, "the module config is still created on purpose"
    assert "qmlSearch: branding" in HOOK
    assert not re.search(r"^[^#\n]*patch_file[^\n]*notesqml", HOOK, re.MULTILINE), (
        "the hook must not patch the Calamares sequence with notesqml again - see Q-68"
    )


def test_image_gates_check_the_assets_and_that_the_step_stays_disabled():
    for name in ("installer notes page assets shipped", "installer notes: German and French translations",
                 "installer notes: module config", "installer notes step stays disabled (Q-68)"):
        assert name in GATE, name
    assert "calamares-hscl1_de.qm" in GATE and "calamares-hscl1_fr.qm" in GATE
