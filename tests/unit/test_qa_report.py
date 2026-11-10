"""qa_report parser/evaluator."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import qa_report as qr  # noqa: E402

GOOD = """== hscl-qa ==
version=1
plasmashell_user=kubuntu

== os-release ==
NAME="HSCL1"
ID=ubuntu

== hscl-status ==
{"os": "HSCL1 x"}

== hscl-doctor ==
{"checks": [], "failed": 0}

== secure-boot ==
SecureBoot enabled

== ufw ==
Status: active

== failed-units ==

== sysctl ==
kernel.kptr_restrict = 2

== user-lookandfeel ==
org.hcs.hscl1.desktop

== end ==
"""


def test_good_report_passes_all_checks():
    checks = qr.evaluate(qr.parse(GOOD))
    assert all(c.ok for c in checks), [c for c in checks if not c.ok]


def test_incomplete_report_is_rejected():
    with pytest.raises(ValueError):
        qr.parse(GOOD.replace("== end ==", ""))


@pytest.mark.parametrize("needle,repl,failing", [
    ('NAME="HSCL1"', 'NAME="Ubuntu"', "os-release NAME is HSCL1"),
    ("Status: active", "Status: inactive", "firewall baseline active"),
    ("org.hcs.hscl1.desktop", "org.kubuntu.desktop", "default look-and-feel is HCS"),
    ("plasmashell_user=kubuntu", "plasmashell_user=none", "desktop session running"),
    ("kernel.kptr_restrict = 2", "kernel.kptr_restrict = 0", "kernel.kptr_restrict = 2"),
])
def test_each_regression_is_detected(needle, repl, failing):
    checks = {c.name: c.ok for c in qr.evaluate(qr.parse(GOOD.replace(needle, repl)))}
    assert checks[failing] is False


def test_the_system_default_counts_as_the_active_look_and_feel():
    """Measured 2026-11-10: a correct live image failed this check because the user's kdeglobals is empty.

    The active look-and-feel on a fresh system is the system default from kubuntu-default-settings, so an
    empty user section plus `org.hcs.hscl1.desktop` in the system section must pass.
    """
    report = GOOD.replace(
        "== user-lookandfeel ==\norg.hcs.hscl1.desktop\n",
        "== user-lookandfeel ==\n\n== system-lookandfeel ==\norg.hcs.hscl1.desktop\n",
    )
    checks = {c.name: c.ok for c in qr.evaluate(qr.parse(report))}
    assert checks["default look-and-feel is HCS"] is True


def test_a_kubuntu_look_and_feel_still_fails_when_only_the_system_default_says_it():
    report = GOOD.replace(
        "== user-lookandfeel ==\norg.hcs.hscl1.desktop\n",
        "== user-lookandfeel ==\n\n== system-lookandfeel ==\norg.kubuntu.desktop\n",
    )
    checks = {c.name: c.ok for c in qr.evaluate(qr.parse(report))}
    assert checks["default look-and-feel is HCS"] is False
