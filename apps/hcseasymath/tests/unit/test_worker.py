"""The isolated worker: limits, killing, output caps, environment hygiene (decision D5)."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

from hcseasymath.jobs.worker import MAX_OUTPUT_BYTES, run_isolated

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="the worker uses POSIX resource limits and process groups; run the gate in WSL/Linux",
)

HELPERS = str(Path(__file__).resolve().parent.parent / "helpers")
REQ = {"operation": "differentiate", "expression": "x**3 - 3*x**2 + 2*x", "variable": "x"}


def test_a_normal_request_runs_in_the_child_and_returns_the_derivative():
    res = run_isolated(REQ, timeout_s=30)
    assert res["status"] == "ok"
    assert res["result_expression"] == "3*x**2 - 6*x + 2"


def test_hostile_input_still_comes_back_as_a_typed_refusal():
    res = run_isolated({**REQ, "expression": "__import__('os').system('true')"}, timeout_s=30)
    assert res["status"] == "invalid_input"


def test_a_stuck_child_is_killed_at_the_wall_clock_limit(tmp_path):
    pid_file = tmp_path / "pid"
    start = time.monotonic()
    res = run_isolated(
        {"pid_file": str(pid_file)},
        timeout_s=1.5,
        entry="child_sleep",
        extra_pythonpath=HELPERS,
    )
    assert res["status"] == "resource_limit"
    assert "time" in res["error"]
    assert time.monotonic() - start < 6.0
    pid = int(pid_file.read_text())
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_a_memory_hog_is_stopped_by_the_address_space_limit():
    res = run_isolated(
        {},
        timeout_s=20,
        memory_bytes=256 * 1024 * 1024,
        entry="child_memory",
        extra_pythonpath=HELPERS,
    )
    assert res["status"] == "resource_limit"


def test_the_real_child_reports_memory_exhaustion_as_a_resource_limit():
    # 48 MiB of address space is not enough to import SymPy.
    res = run_isolated(REQ, timeout_s=30, memory_bytes=48 * 1024 * 1024)
    assert res["status"] == "resource_limit"
    assert res["result_expression"] is None


def test_output_flood_is_capped_not_buffered_forever():
    res = run_isolated({}, timeout_s=20, entry="child_flood", extra_pythonpath=HELPERS)
    assert res["status"] in {"resource_limit", "internal_error"}
    assert MAX_OUTPUT_BYTES <= 1024 * 1024


def test_the_child_does_not_inherit_the_parents_environment(monkeypatch):
    monkeypatch.setenv("HCS_FAKE_SECRET", "do-not-leak")
    res = run_isolated({}, timeout_s=20, entry="child_env", extra_pythonpath=HELPERS)
    assert res.get("env_keys") is not None
    assert "HCS_FAKE_SECRET" not in res["env_keys"]
    assert set(res["env_keys"]) <= {"PATH", "PYTHONPATH", "LANG", "LC_ALL", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE"}


def test_two_runs_do_not_share_state():
    a = run_isolated(REQ, timeout_s=30)
    b = run_isolated({**REQ, "expression": "x**2"}, timeout_s=30)
    assert a["result_expression"] != b["result_expression"]
    json.dumps(a), json.dumps(b)
