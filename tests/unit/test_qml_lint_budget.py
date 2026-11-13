"""Q-19: our own QML must lint clean, and the two pools must stay apart.

The Control Center reached **0** qmllint warnings on 2026-11-13: model roles are declared as `required
property`, the pages carry `pragma ComponentBehavior: Bound` so a delegate may reference the enclosing page's
ids, and the single unresolvable C++ context property is suppressed on its own line with a reason.

The Plasma wallpaper plugin keeps a separate allowance, because qmllint cannot resolve
`org.kde.plasma.plasmoid`, `org.kde.kirigami` or `org.kde.kcmutils` on a host without the Plasma QML modules
and every unresolved type cascades into more warnings. Collapsing the two pools back into one number is what
this file prevents: it would let a real regression in our code hide behind the plugin's noise.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/dev/qml-gate.sh"
CC = ROOT / "apps/control-center/qml"
PROVE = ROOT / "scripts/dev/test-qml-gate-ratchet.sh"


def test_the_control_center_has_its_own_zero_budget():
    text = GATE.read_text(encoding="utf-8")
    assert 'lint_area "control-center" apps/control-center/qml "${QML_CC_WARN_BUDGET:-0}"' in text, (
        "the Control Center must be linted with its own budget, defaulting to 0"
    )
    assert 'lint_area "rain wallpaper"' in text, "the plugin keeps a separate, documented allowance"


def test_the_plugin_allowance_carries_a_reason():
    text = GATE.read_text(encoding="utf-8")
    assert "Plasma/Kirigami/KCM QML modules not being installed" in text, (
        "an allowance without a reason is a hole"
    )
    m = re.search(r"QML_WP_WARN_BUDGET:-(\d+)", text)
    assert m, "the plugin budget must be visible and overridable"
    assert int(m.group(1)) > 0, "a zero plugin budget would need the Plasma modules to be installed first"


def test_the_gate_still_fails_on_syntax_errors_and_errors():
    text = GATE.read_text(encoding="utf-8")
    assert "grep -cE '^Error:|\\[syntax\\]'" in text
    assert text.count("exit 1") >= 2, "both the error path and the budget path must exit non-zero"


def test_the_proof_script_exists_and_is_executable():
    assert PROVE.is_file(), "the ratchet needs its own proof, not just an assertion"
    assert "ZzProbe.qml" in PROVE.read_text(encoding="utf-8"), "the proof must add a real violating file"


def test_no_page_carries_an_unexplained_lint_suppression():
    """A `qmllint disable` is allowed only with a reason on the same block."""
    offenders = []
    for path in sorted(CC.rglob("*.qml")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if re.match(r"\s*//\s*qmllint disable\b", line):
                context = "\n".join(lines[max(0, i - 4):i])
                if not re.search(r"context propert|\bQ-\d+\b|unresolvable", context):
                    offenders.append(f"{path.relative_to(ROOT)}:{i + 1}")
    assert not offenders, f"undocumented qmllint suppression: {offenders}"


def test_the_pages_that_use_delegates_with_outer_ids_declare_bound_behaviour():
    for name in ("pages/AppearancePage.qml", "pages/SecurityPage.qml", "components/NavRail.qml"):
        text = (CC / name).read_text(encoding="utf-8")
        assert text.splitlines()[0].strip() == "pragma ComponentBehavior: Bound", (
            f"{name} needs the pragma, otherwise qmllint flags every outer-id reference in its delegates"
        )
