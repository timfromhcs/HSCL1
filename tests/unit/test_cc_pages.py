"""Control Center: page/rail parity, the shared page frame, and a bridge allowlist that matches the pages.

Two failure classes are prevented here, both observed in this repository:

* a page that is not wired into the `StackLayout` (shipped but unreachable) or a rail label without a page -
  the page count and the label count could drift apart on every edit;
* a page that asks the CLI for a command `CliBackend::isAllowed` refuses. The Miner page did exactly that and
  could only ever paint its error banner although `hscl` answered fine (measured 2026-11-11, Q-62).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CC = ROOT / "apps/control-center"
QML = CC / "qml"
MARKER = "static const QList<QStringList> fixed"


def page_files() -> list[Path]:
    return sorted((QML / "pages").glob("*Page.qml"))


def main_text() -> str:
    return (QML / "Main.qml").read_text(encoding="utf-8")


def stack_pages() -> list[str]:
    return re.findall(r"^\s{12}(\w+Page)\s*\{\s*backend:", main_text(), re.MULTILINE)


def rail_titles() -> list[str]:
    block = re.search(r"readonly property var pageTitles:\s*\[(.*?)\]", main_text(), re.S)
    assert block, "Main.qml has no pageTitles list"
    return re.findall(r'qsTr\("((?:[^"\\]|\\.)*)"\)', block.group(1))


def allowlist() -> set[tuple[str, ...]]:
    text = (CC / "src/CliBackend.cpp").read_text(encoding="utf-8")
    start = text.index(MARKER)
    end = text.index("};", start)
    rows = set()
    # One line can carry several lists (`{"version"}, {"about"}, ...`), so parse every brace group inside
    # the initializer and keep the ones that contain nothing but string literals.
    for group in re.findall(r"\{([^{}]*)\}", text[start:end]):
        command = tuple(re.findall(r'"([^"]*)"', group))
        if command:
            rows.add(command)
    return rows


def test_every_page_is_wired_and_every_rail_label_has_a_page():
    pages = [p.stem for p in page_files()]
    assert pages, "no page files found"
    stack = stack_pages()
    assert sorted(stack) == pages, (
        "every page file must appear in the StackLayout exactly once",
        stack,
        pages,
    )
    titles = rail_titles()
    assert len(titles) == len(stack), (titles, stack)
    assert len(set(titles)) == len(titles), f"duplicate rail labels: {titles}"


def test_every_page_uses_the_shared_frame_and_a_localised_title():
    for path in page_files():
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^HcsPage\s*\{", text, re.MULTILINE), f"{path.name}: root must be HcsPage"
        assert re.search(r"^\s{4}title:\s*qsTr\(", text, re.MULTILINE), f"{path.name}: no localised title"


def test_every_static_fetcher_command_is_allowed_by_the_bridge():
    allowed = allowlist()
    assert len(allowed) >= 10, "the allowlist parser found almost nothing - it would pass vacuously"
    checked = 0
    problems = []
    for path in page_files():
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"args:\s*\[([^\]]*)\]", text):
            raw = match.group(1)
            if not re.fullmatch(r'\s*(?:"[^"]*"\s*,?\s*)+', raw):
                continue  # empty or dynamic (`["miner", "probe", page.device]`) is tested by the QML suite
            command = tuple(re.findall(r'"([^"]*)"', raw))
            checked += 1
            if command not in allowed:
                problems.append((path.name, list(command)))
    assert checked >= 12, f"only {checked} static requests found - the gate would pass without looking"
    assert not problems, f"pages ask for commands the bridge refuses: {problems}"


def test_the_typography_token_is_applied():
    """Theme.fontFamily was a dead token until 2026-11-13: nothing applied it to the running application."""
    theme = (QML / "Theme.qml").read_text(encoding="utf-8")
    assert 'fontFamily: "Inter"' in theme
    src = (CC / "src/main.cpp").read_text(encoding="utf-8")
    assert "QFontDatabase::families" in src and "QGuiApplication::setFont" in src


def test_the_bridge_does_not_allow_a_setter_or_an_installer():
    allowed = allowlist()
    forbidden = [
        ("system", "updates"),
        ("system", "updates", "--install"),
        ("lab", "run"),
        ("lab", "toolset", "install", "basic"),
        ("dev", "setup"),
        ("language", "set", "de"),
        ("recovery", "snapshots", "create"),
        ("privacy", "tor"),
    ]
    for command in forbidden:
        assert command not in allowed, f"the UI bridge must not reach {command}"
