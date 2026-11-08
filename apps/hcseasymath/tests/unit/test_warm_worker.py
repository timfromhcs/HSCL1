"""The warm worker: a pre-imported zygote that forks one isolated child per request."""

import os
import signal
import sys
import threading
import time
from pathlib import Path

import pytest

from hcseasymath.jobs.warm import WarmWorker

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="the warm worker uses fork, unix sockets and POSIX limits; run the gate in WSL/Linux",
)

REQ = {"operation": "differentiate", "expression": "x**3 - 3*x**2 + 2*x", "variable": "x"}


@pytest.fixture(scope="module")
def worker():
    w = WarmWorker()
    w.start()
    yield w
    w.stop()


def test_a_normal_request_returns_the_derivative(worker):
    res = worker.run(REQ, timeout_s=30)
    assert res["status"] == "ok" and res["result_expression"] == "3*x**2 - 6*x + 2"


def test_result_equals_the_cold_worker_result(worker):
    from hcseasymath.jobs.worker import run_isolated

    warm, cold = worker.run(REQ, timeout_s=30), run_isolated(REQ, timeout_s=30)
    for key in ("status", "result_expression", "run_id", "input_digest", "exactness", "checks"):
        assert warm[key] == cold[key]


def test_hostile_input_is_a_typed_refusal(worker):
    res = worker.run({**REQ, "expression": "__import__('os').system('true')"}, timeout_s=30)
    assert res["status"] == "invalid_input"


def test_a_warm_request_is_much_faster_than_a_cold_start(worker):
    worker.run(REQ, timeout_s=30)
    start = time.perf_counter()
    worker.run(REQ, timeout_s=30)
    assert time.perf_counter() - start < 0.3  # a cold child needs about 0.5 s for the imports alone


def test_each_request_runs_in_its_own_process(worker):
    worker.run(REQ, timeout_s=30)
    first = worker.last_child_pid
    worker.run(REQ, timeout_s=30)
    assert worker.last_child_pid != first
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(first, 0)  # reaped, not left behind


def test_the_time_limit_kills_the_child_and_says_so(worker):
    res = worker.run({"operation": "simplify", "expression": "sin(x)**2 + cos(x)**2", "variable": "x"}, timeout_s=0.001)
    assert res["status"] == "resource_limit" and "time" in res["error"]
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(worker.last_child_pid, 0)


def test_a_stuck_child_is_really_killed_at_the_time_limit(tmp_path):
    helpers = str(Path(__file__).resolve().parent.parent / "helpers")
    stuck = WarmWorker(engine="slow_engine:execute", extra_pythonpath=helpers)
    stuck.start()
    try:
        pid_file = tmp_path / "pid"
        start = time.monotonic()
        res = stuck.run({"operation": "x", "pid_file": str(pid_file)}, timeout_s=1.5)
        assert res["status"] == "resource_limit" and "time" in res["error"]
        assert time.monotonic() - start < 6.0
        pid = int(pid_file.read_text())
        time.sleep(0.2)
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    finally:
        stuck.stop()


def test_the_memory_limit_is_enforced_in_the_child(worker):
    res = worker.run(REQ, timeout_s=30, memory_bytes=64 * 1024 * 1024)
    assert res["status"] == "resource_limit"
    assert worker.run(REQ, timeout_s=30)["status"] == "ok"  # the zygote itself is unharmed


def test_a_dead_zygote_is_restarted(worker):
    os.kill(worker.zygote_pid, signal.SIGKILL)
    time.sleep(0.2)
    assert worker.run(REQ, timeout_s=30)["status"] == "ok"


def test_the_zygote_does_not_inherit_the_callers_environment(worker, monkeypatch):
    monkeypatch.setenv("HCSEM_SECRET_PROBE", "leak")
    worker.stop()
    worker.start()
    with open(f"/proc/{worker.zygote_pid}/environ", "rb") as fh:
        names = {item.split(b"=", 1)[0] for item in fh.read().split(b"\0") if item}
    assert b"HCSEM_SECRET_PROBE" not in names
    assert names <= {b"PATH", b"PYTHONPATH", b"LANG", b"LC_ALL", b"PYTHONHASHSEED", b"PYTHONDONTWRITEBYTECODE"}


def test_requests_in_parallel_do_not_mix_up(worker):
    out: dict[int, str] = {}

    def go(i: int) -> None:
        r = worker.run({**REQ, "expression": f"x**{i + 2}"}, timeout_s=30)
        out[i] = r["result_expression"]

    threads = [threading.Thread(target=go, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert out == {i: f"{i + 2}*x**{i + 1}" if i > 0 else "2*x" for i in range(6)}


def test_a_socket_directory_is_private(worker):
    assert (os.stat(worker.socket_dir).st_mode & 0o777) == 0o700
