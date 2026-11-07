"""G3: the parsers that see untrusted text must survive it.

`proptest` cases live in the Rust modules (they need the private functions); this test makes sure the
gate cannot rot silently: the property modules must exist, and a `cargo test` run of exactly those
cases must pass. Slow fuzzing is not run here - `.github/workflows/fuzz.yml` does that on a schedule.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "redact.rs": ["proptest! {", "prop_redaction_is_idempotent"],
    "toolcall.rs": ["proptest! {", "prop_parse_never_panics"],
    "hw.rs": ["proptest! {", "prop_parse_hex_round_trips"],
}
CARGO = shutil.which("cargo")


@pytest.mark.parametrize("module,markers", sorted(SOURCES.items()))
def test_property_module_exists_in_the_source(module, markers):
    text = (ROOT / "cli/hscl/src" / module).read_text(encoding="utf-8")
    for marker in markers:
        assert marker in text, f"{module} misses {marker!r} (G3 property tests)"


def test_proptest_is_a_dev_dependency_only():
    """It must not end up in the shipped binary (size, licence surface)."""
    text = (ROOT / "cli/hscl/Cargo.toml").read_text(encoding="utf-8")
    dev = text.split("[dev-dependencies]", 1)
    assert len(dev) == 2, "no [dev-dependencies] section"
    assert "proptest" in dev[1]
    assert "proptest" not in dev[0], "proptest must not be a runtime dependency"


def test_the_fuzz_workflow_is_time_boxed_and_scheduled():
    wf = (ROOT / ".github/workflows/fuzz.yml").read_text(encoding="utf-8")
    assert "schedule:" in wf and "workflow_dispatch:" in wf, "fuzzing must be scheduled, not per-PR"
    assert "-max_total_time=" in wf, "a fuzz run without a time box can hang the job"
    assert "cargo-fuzz" in wf or "cargo fuzz" in wf


@pytest.mark.skipif(CARGO is None, reason="cargo not installed on this host")
def test_the_property_cases_pass_on_this_host():
    r = subprocess.run([CARGO, "test", "-q", "-p", "hscl", "--", "prop_"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
