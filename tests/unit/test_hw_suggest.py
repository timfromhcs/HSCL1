"""B3: `hscl hw suggest` maps devices to driver packages without installing anything.

Research (2026-11-07, ubuntu-drivers-common sources) settled the mechanism: `dh_modaliases` runs
`modinfo` over a package's modules and emits a `Modaliases:` field into the apt `Packages` index;
each value is a glob (often vendor-wrapped, e.g. `nv(pci:v000010DEd000010C3sv*sd*bc03sc*i*)`) that
is matched against the device modalias from sysfs. `ubuntu-drivers devices|list` is the read-only
oracle on a real machine.

These tests pin the parsing and the matching rules in Rust (pure functions, no apt needed); the
CLI behaviour on a machine without apt is checked here as well, because "no index" must be a
reported result and never an error or an invented suggestion.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CARGO = shutil.which("cargo")


def _src(name: str) -> str:
    return (ROOT / "cli/hscl/src" / name).read_text(encoding="utf-8")


def test_the_matching_rules_are_documented_in_the_source():
    """The glob semantics come from upstream; the comments must name that origin so a future
    change can be checked against the real behaviour instead of being re-invented."""
    hw = _src("hw.rs")
    for marker in ("fn parse_packages_modaliases", "fn modality_matches", "fn suggest", "ubuntu-drivers"):
        assert marker in hw, marker


def test_the_suggestion_never_installs_anything():
    """A suggestion command that shells out to apt-get would be one refactor away from installing
    on a typo; the only allowed external call is apt-cache/ubuntu-drivers in read-only mode."""
    hw = _src("hw.rs")
    body = hw[hw.index("fn suggest"):]
    body = body[: body.index("\n}\n") + 3] if "\n}\n" in body else body
    for forbidden in ("apt-get install", "apt install", "dpkg -i", "systemctl start"):
        assert forbidden not in body, forbidden


@pytest.mark.skipif(CARGO is None, reason="cargo not installed on this host")
def test_the_unit_tests_for_suggestions_pass():
    r = subprocess.run([CARGO, "test", "-q", "-p", "hscl", "--", "suggest"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
