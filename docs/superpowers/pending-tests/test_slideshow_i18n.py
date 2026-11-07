"""The installer slideshow must follow the installer language through qsTr and the branding .qm files, not through Qt.locale().

Found 2026-11-07: Qt.locale().name stays en_US when the installer language is switched (seen for the notes page), so the old
`tr(en, de, fr)` helper in show.qml always showed English. Same fix as for notesqml.qml; context name is the file base name `show`.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "packages/debian/hscl-branding/etc/calamares/branding/hscl1/show.qml"
I18N = ROOT / "distro/installer/i18n"


def sources():
    text = QML.read_text(encoding="utf-8")
    return [s.replace('\\"', '"') for s in re.findall(r'qsTr\("((?:[^"\]|\.)*)"\)', text)], text


def messages(lang):
    root = ET.parse(I18N / f"calamares-hscl1_{lang}.ts").getroot()
    ctx = {c.findtext("name"): c for c in root.findall("context")}
    assert "show" in ctx, f"{lang}: no context 'show'"
    out = {}
    for m in ctx["show"].findall("message"):
        tr = m.find("translation")
        out[m.findtext("source")] = (tr.text or "", tr.get("type"))
    return out


def test_slideshow_does_not_choose_text_by_locale():
    _, text = sources()
    assert "Qt.locale" not in text
    assert not re.search(r"function\s+tr\s*\(", text)


def test_slideshow_has_its_visible_texts_as_qsTr():
    srcs, _ = sources()
    joined = " ".join(srcs)
    assert len(srcs) >= 3, srcs
    assert "Made with love by hcsmedia" in joined
    assert "sends no telemetry" in joined
    assert "Handbook" in joined


def test_every_slideshow_string_is_translated_to_german_and_french():
    srcs, _ = sources()
    for lang in ("de", "fr"):
        msgs = messages(lang)
        for s in srcs:
            assert s in msgs, f"{lang}: missing {s[:50]!r}"
            text, kind = msgs[s]
            assert text.strip() and text != s and kind not in ("unfinished", "vanished", "obsolete"), f"{lang}: {s[:50]!r}"


def test_no_stale_slideshow_translations():
    srcs, _ = sources()
    for lang in ("de", "fr"):
        assert set(messages(lang)) <= set(srcs), lang


def test_the_notes_page_translations_are_untouched():
    for lang in ("de", "fr"):
        root = ET.parse(I18N / f"calamares-hscl1_{lang}.ts").getroot()
        names = [c.findtext("name") for c in root.findall("context")]
        assert "notesqml" in names and names.count("notesqml") == 1 and names.count("show") == 1
