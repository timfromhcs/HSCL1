"""Rain wallpaper plugin: package structure, token colours, config schema, and (where Qt is available) the QML tests."""
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain"
TOKENS = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))["themes"]["hcs-midnight"]


def test_metadata_and_files():
    m = json.loads((P / "metadata.json").read_text(encoding="utf-8"))
    assert m["KPackageStructure"] == "Plasma/Wallpaper" and m["KPlugin"]["Id"] == "org.hcs.hscl1.rain"
    for f in ("contents/ui/main.qml", "contents/ui/RainField.qml", "contents/ui/StarField.qml", "contents/ui/AuroraField.qml", "contents/ui/GridField.qml", "contents/ui/config.qml", "contents/config/main.xml"):
        assert (P / f).is_file(), f


def test_config_schema_has_bounded_entries():
    ns = {"k": "http://www.kde.org/standards/kcfg/1.0"}
    root = ET.parse(P / "contents/config/main.xml").getroot()
    entries = {e.get("name"): e for e in root.iterfind(".//k:entry", ns)}
    assert set(entries) == {"Effect", "Density", "Speed", "ShowMark", "Accent", "Background"}
    for n in ("Density", "Speed"):
        assert entries[n].find("k:min", ns).text == "1" and entries[n].find("k:max", ns).text == "3"


def test_colours_come_from_the_design_tokens():
    qml = (P / "contents/ui/RainField.qml").read_text(encoding="utf-8").lower()
    assert f'background: "{TOKENS["surface-0"]}"' in qml
    assert f'glyphcolor: "{TOKENS["accent"]}"' in qml
    assert f'headcolor: "{TOKENS["text-primary"]}"' in qml


def test_main_respects_the_system_animation_setting():
    main = (P / "contents/ui/main.qml").read_text(encoding="utf-8")
    assert "animate: Kirigami.Units.longDuration > 0" in main
    for effect in ("rain", "starfield", "aurora", "grid"):
        assert effect in main


def qmltestrunner():
    return shutil.which("qmltestrunner6") or (Path("/usr/lib/qt6/bin/qmltestrunner").exists() and "/usr/lib/qt6/bin/qmltestrunner") or None


@pytest.mark.skipif(not qmltestrunner(), reason="Qt 6 qmltestrunner not installed on this host (run in the WSL builder)")
def test_qml_unit_tests_pass():
    r = subprocess.run([qmltestrunner(), "-input", str(ROOT / "tests/qml_plugin")], capture_output=True, text=True,
                       env={"QT_QPA_PLATFORM": "offscreen", "PATH": "/usr/bin:/bin"}, timeout=120)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-500:]
