"""Control Center: every qsTr() string has a non-empty German and French translation in the right context; Theme.qml is in sync."""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CC = ROOT / "apps/control-center"


def source_strings():
    found = {}
    for qml in (CC / "qml").rglob("*.qml"):
        if qml.name == "Theme.qml":
            continue
        for s in re.findall(r'qsTr\("((?:[^"\\]|\\.)*)"\)', qml.read_text(encoding="utf-8")):
            found.setdefault(qml.stem, set()).add(s)
    return found


def translations(lang):
    root = ET.parse(CC / f"i18n/hscl-cc_{lang}.ts").getroot()
    out = {}
    for ctx in root.findall("context"):
        name = ctx.findtext("name")
        for m in ctx.findall("message"):
            out[(name, m.findtext("source"))] = (m.findtext("translation") or "").strip()
    return out


def test_every_string_is_translated_in_de_and_fr():
    src = source_strings()
    assert sum(len(v) for v in src.values()) > 40
    for lang in ("de", "fr"):
        tr = translations(lang)
        for ctx, strings in src.items():
            for s in strings:
                assert tr.get((ctx, s)), f"{lang}: missing translation for {ctx}: {s!r}"


def test_no_translation_is_left_untranslated_by_accident():
    # identical source/translation is only acceptable for product names and technical terms
    allowed_same = {"Secure Boot", "AppArmor", "System", "Kernel", "Status", "Version", "Navigation", "Firewall", "%1 MiB", "Plan: %1"}
    for lang in ("de", "fr"):
        for (ctx, s), t in translations(lang).items():
            if t == s:
                assert s in allowed_same, f"{lang}: {ctx}: {s!r} not translated"


def test_theme_qml_is_generated_from_tokens():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/gen_qml_theme.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
