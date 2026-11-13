"""Accessibility gate for the Control Center QML.

The state audited on 2026-11-10 is good - every page title is a heading, every button carries a context-rich
`Accessible.name`, there is no animation at all (reduced motion by construction) and the navigation rail is
keyboard-driven with its own QML test. Nothing pinned that, so the next edit could silently drop it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "apps/control-center/qml"
CONTROLS = ("Button", "HcsButton", "ToolButton", "CheckBox", "Switch", "RadioButton", "ComboBox", "Slider", "TextField")


def blocks(text: str, control: str):
    """Yield the body of every `Control {` block, using brace matching so nested items are included."""
    for match in re.finditer(rf"(?m)^(\s*){control}\s*\{{", text):
        start = text.index("{", match.start())
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : i + 1]
                    break


def test_every_control_has_an_accessible_name():
    problems = []
    checked = 0
    for path in sorted(QML.rglob("*.qml")):
        # HcsButton is the base widget itself: it declares the role, while the name is supplied by each call
        # site (the HcsButton usages are scanned like every other control).
        base = path.name == "HcsButton.qml"
        text = path.read_text(encoding="utf-8")
        if base:
            assert "Accessible.role: Accessible.Button" in text
        for control in CONTROLS:
            for body in blocks(text, control):
                if base:
                    continue
                checked += 1
                if "Accessible.name" not in body:
                    problems.append(f"{path.name}: {control} without Accessible.name")
    assert checked >= 3, f"only {checked} controls found - the gate would pass without looking"
    assert not problems, problems


def test_every_page_title_is_a_heading():
    # One shared frame owns the heading, so the heading level cannot drift per page. The frame must declare
    # both the role and a name, and every page must go through it.
    frame = (QML / "components/HcsPage.qml").read_text(encoding="utf-8")
    assert "font.pixelSize: Theme.font2xl" in frame, "HcsPage has no page-title size"
    assert "font.bold: true" in frame, "HcsPage has no bold page title"
    assert "Accessible.Heading" in frame and "Accessible.name: page.title" in frame
    for path in sorted((QML / "pages").glob("*Page.qml")):
        text = path.read_text(encoding="utf-8")
        assert "font2xl" not in text, f"{path.name}: page draws its own heading instead of using HcsPage"
        assert "Accessible.Heading" not in text, f"{path.name}: page declares its own heading"


def test_the_control_center_does_not_animate():
    """Reduced motion is honoured by having nothing to reduce: the Control Center must stay animation-free."""
    offenders = []
    for path in sorted(QML.rglob("*.qml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\b(Behavior|NumberAnimation|PropertyAnimation|SequentialAnimation|Transition)\b", line):
                offenders.append(f"{path.name}:{number}: {line.strip()[:60]}")
    assert not offenders, offenders


def test_the_keyboard_navigation_test_still_exists():
    suite = (ROOT / "apps/control-center/tests/qml/tst_pages.qml").read_text(encoding="utf-8")
    assert "function test_nav_rail_keyboard_selection()" in suite
    assert "Accessible" in (QML / "components/NavRail.qml").read_text(encoding="utf-8")
