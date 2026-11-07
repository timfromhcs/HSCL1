"""Delegate v2 (plan 2026-11-07-local-agents-v2, Track 1): host gate, single-flight lock, residency-aware memory cost, server wiring.

Measured background: with two local_code runs and a QEMU VM the host hit CPU 100 % and 2.7 GB free RAM, the guests froze; the 8080 server
costs about 1.3 GB asleep and 2.7-3.5 GB working, so counting it as 0 MB hid the real cost.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "local_worker"))

import hostgate  # noqa: E402
import server  # noqa: E402


# ---- host gate (pure) ------------------------------------------------------------------------------------------------------------
def test_idle_host_is_ok():
    d = hostgate.decide_host(cpu_pct=20, qemu_running=False, free_mb=8000, need_mb=1000, reserve_mb=3000)
    assert d["ok"] is True


def test_a_running_vm_blocks_the_model():
    d = hostgate.decide_host(cpu_pct=10, qemu_running=True, free_mb=9000, need_mb=1000, reserve_mb=3000)
    assert d["ok"] is False and "vm" in d["reason"].lower()


def test_high_cpu_blocks_the_model():
    d = hostgate.decide_host(cpu_pct=96, qemu_running=False, free_mb=9000, need_mb=1000, reserve_mb=3000)
    assert d["ok"] is False and "cpu" in d["reason"].lower()


def test_low_memory_blocks_the_model_with_the_shortfall():
    d = hostgate.decide_host(cpu_pct=10, qemu_running=False, free_mb=2700, need_mb=2700, reserve_mb=3000)
    assert d["ok"] is False and "short by 3000" in d["reason"]


def test_override_flags_allow_a_vm_and_busy_cpu_but_never_low_memory():
    d = hostgate.decide_host(cpu_pct=99, qemu_running=True, free_mb=9000, need_mb=1000, reserve_mb=3000, allow_vm=True, cpu_limit=100)
    assert d["ok"] is True
    d = hostgate.decide_host(cpu_pct=1, qemu_running=False, free_mb=100, need_mb=1000, reserve_mb=3000, allow_vm=True, cpu_limit=100)
    assert d["ok"] is False


def test_negative_numbers_are_refused():
    with pytest.raises(ValueError):
        hostgate.decide_host(cpu_pct=-1, qemu_running=False, free_mb=1, need_mb=1, reserve_mb=1)


# ---- residency-aware memory cost ------------------------------------------------------------------------------------------------
TABLE = {"qwen3-4b": 4300, "jev-1.5b": 0, "bonsai-4b": 3900}
WAKE = {"jev-1.5b": 2700}
PROC = {"jev-1.5b": "llama-server"}


def test_resident_shared_server_costs_nothing_extra():
    mb = hostgate.effective_model_mb("jev-1.5b", TABLE, WAKE, PROC, resident_mb=lambda p: 2600)
    assert mb == 0


def test_sleeping_or_missing_shared_server_costs_its_wake_memory():
    assert hostgate.effective_model_mb("jev-1.5b", TABLE, WAKE, PROC, resident_mb=lambda p: 1300) == 2700
    assert hostgate.effective_model_mb("jev-1.5b", TABLE, WAKE, PROC, resident_mb=lambda p: 0) == 2700


def test_other_models_use_the_table_unchanged():
    assert hostgate.effective_model_mb("qwen3-4b", TABLE, WAKE, PROC, resident_mb=lambda p: 0) == 4300
    assert hostgate.effective_model_mb("unknown-x", TABLE, WAKE, PROC, resident_mb=lambda p: 0, default_mb=6000) == 6000


# ---- single flight ---------------------------------------------------------------------------------------------------------------
def test_second_acquire_is_refused_until_release(tmp_path):
    lock = tmp_path / "w.lock"
    a = hostgate.SingleFlight(lock)
    b = hostgate.SingleFlight(lock)
    with a:
        with pytest.raises(hostgate.Busy):
            b.__enter__()
    with b:  # released by a
        pass


def test_stale_lock_of_a_dead_process_is_taken_over(tmp_path):
    lock = tmp_path / "w.lock"
    lock.write_text(json.dumps({"pid": 2**22 + 12345, "t": 0}), encoding="utf-8")  # no such pid
    with hostgate.SingleFlight(lock):
        assert json.loads(lock.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert not lock.exists()


def test_garbage_lock_file_counts_as_stale(tmp_path):
    lock = tmp_path / "w.lock"
    lock.write_text("not json", encoding="utf-8")
    with hostgate.SingleFlight(lock):
        pass


# ---- server wiring ---------------------------------------------------------------------------------------------------------------
def call_args(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    return {"task": "t", "files": ["a.py"], "test_cmd": ["pytest"], "model": "jev-1.5b"}


class FakeRes:
    ok, rounds, reason, diff, last_output = True, 1, "tests passed", "", ""


def make_deps(tmp_path, host_ok=True, lock=None, ran=None):
    ran = ran if ran is not None else []

    def run_task(*a, **k):
        ran.append(1)
        return FakeRes()

    return server.Deps(
        root=tmp_path, run_task=run_task, make_chat=lambda m: (lambda msgs: ""), gate=lambda m: {"ok": True, "reason": "ok"},
        host=lambda: {"ok": host_ok, "reason": "a VM is running (qemu)" if not host_ok else "idle"},
        lock=lock or (lambda: hostgate.SingleFlight(tmp_path / "w.lock")),
    ), ran


def test_busy_host_is_a_tool_error_and_runs_nothing(tmp_path):
    deps, ran = make_deps(tmp_path, host_ok=False)
    r = server._call(call_args(tmp_path), deps)
    assert r["isError"] is True and "host_busy" in r["content"][0]["text"] and "VM" in r["content"][0]["text"]
    assert ran == []


def test_second_concurrent_call_gets_busy_and_runs_nothing(tmp_path):
    deps, ran = make_deps(tmp_path)
    with hostgate.SingleFlight(tmp_path / "w.lock"):  # a call is "running"
        r = server._call(call_args(tmp_path), deps)
    assert r["isError"] is True and r["content"][0]["text"].startswith("busy:")
    assert ran == []


def test_normal_call_still_works_and_releases_the_lock(tmp_path):
    deps, ran = make_deps(tmp_path)
    r = server._call(call_args(tmp_path), deps)
    assert r["isError"] is False and ran == [1]
    assert not (tmp_path / "w.lock").exists()


def test_existing_four_field_deps_still_construct():
    d = server.Deps(root=Path("."), run_task=lambda *a, **k: None, make_chat=lambda m: None, gate=lambda m: {"ok": True, "reason": ""})
    assert callable(d.host) and callable(d.lock)
