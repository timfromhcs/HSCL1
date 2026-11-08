"""Durable self-heal scheduler tick (ledger row 8): the seven tests of docs/research/SELFHEAL_SCHEDULER_DESIGN.md plus the edges."""
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "selfheal"))

import tick  # noqa: E402

PY = sys.executable


def row(row_id, code, heavy=False):
    return {"id": row_id, "argv": [PY, "-c", code], "heavy": heavy}


def make(tmp_path, rows, **kw):
    return tick.Tick(state_dir=tmp_path, rows=rows, **kw)


def lines(tmp_path):
    log = tmp_path / "tick.log.jsonl"
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_two_ticks_started_together_run_exactly_one(tmp_path):
    rows = [row("slow", "import time; time.sleep(1.0)")]
    results = []
    barrier = threading.Barrier(2)

    def go():
        t = make(tmp_path, rows)
        barrier.wait()
        results.append(t.run(dry_run=False)["outcome"])

    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["ok", "skipped: locked"]


def test_a_stale_lock_is_taken_over_and_a_fresh_one_is_not(tmp_path):
    rows = [row("quick", "pass")]
    lock = tmp_path / "global.lock"
    lock.write_text(json.dumps({"pid": 1, "started": time.time() - 10_000}))
    assert make(tmp_path, rows, stale_after=300).run(dry_run=False)["outcome"] == "ok"
    lock.write_text(json.dumps({"pid": 1, "started": time.time()}))
    assert make(tmp_path, rows, stale_after=300).run(dry_run=False)["outcome"] == "skipped: locked"
    assert lock.exists(), "a live lock must not be removed by the tick that skipped"


def test_a_worker_past_the_timeout_is_killed_and_recorded(tmp_path):
    pid_file = tmp_path / "pid"
    code = f"import os,time; open({str(pid_file)!r},'w').write(str(os.getpid())); time.sleep(600)"
    start = time.monotonic()
    res = make(tmp_path, [row("hang", code)], tick_limit=1.0).run(dry_run=False)
    assert res["outcome"] == "timeout" and time.monotonic() - start < 8
    time.sleep(0.3)
    pid = int(pid_file.read_text())
    if sys.platform.startswith("linux"):
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    assert lines(tmp_path)[-1]["outcome"] == "timeout"


def test_a_held_heavy_lock_defers_a_heavy_row(tmp_path):
    (tmp_path / "heavy.lock").write_text(json.dumps({"pid": 1, "started": time.time()}))
    res = make(tmp_path, [row("vm", "pass", heavy=True)]).run(dry_run=False)
    assert res["outcome"] == "deferred" and res["row"] == "vm"
    assert lines(tmp_path)[-1]["outcome"] == "deferred"


def test_a_light_row_runs_while_the_heavy_lock_is_held(tmp_path):
    (tmp_path / "heavy.lock").write_text(json.dumps({"pid": 1, "started": time.time()}))
    assert make(tmp_path, [row("light", "pass")]).run(dry_run=False)["outcome"] == "ok"


def test_the_third_consecutive_failure_blocks_the_row_and_the_next_row_is_picked(tmp_path):
    rows = [row("bad", "raise SystemExit(3)"), row("good", "pass")]
    outcomes = [make(tmp_path, rows).run(dry_run=False) for _ in range(5)]
    assert [o["row"] for o in outcomes[:3]] == ["bad", "bad", "bad"]
    assert [o["outcome"] for o in outcomes[:3]] == ["failed", "failed", "blocked"]
    assert [o["row"] for o in outcomes[3:]] == ["good", "good"]
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["rows"]["bad"]["blocked"] is True


def test_a_success_resets_the_failure_count(tmp_path):
    flag = tmp_path / "flag"
    code = f"import pathlib,sys; p=pathlib.Path({str(flag)!r}); sys.exit(0 if p.exists() else 3)"
    rows = [row("flaky", code)]
    make(tmp_path, rows).run(dry_run=False)
    make(tmp_path, rows).run(dry_run=False)
    flag.write_text("x")
    assert make(tmp_path, rows).run(dry_run=False)["outcome"] == "ok"
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["rows"]["flaky"]["failures"] == 0 and not state["rows"]["flaky"].get("blocked")


def test_dry_run_changes_no_state_and_runs_nothing(tmp_path):
    marker = tmp_path / "ran"
    rows = [row("r", f"open({str(marker)!r},'w').write('x')")]
    make(tmp_path, rows).run(dry_run=False)
    marker.unlink()
    before = (tmp_path / "state.json").read_bytes()
    res = make(tmp_path, rows).run(dry_run=True)
    assert res["outcome"] == "dry-run" and res["row"] == "r" and res["argv"] == rows[0]["argv"]
    assert (tmp_path / "state.json").read_bytes() == before
    assert not marker.exists()
    assert not (tmp_path / "global.lock").exists()
    assert lines(tmp_path)[-1]["outcome"] == "dry-run"  # the log line is the only write


def test_a_corrupt_state_file_is_refused_and_not_overwritten(tmp_path):
    (tmp_path / "state.json").write_text("{not json")
    res = make(tmp_path, [row("r", "pass")]).run(dry_run=False)
    assert res["outcome"] == "refused: corrupt state"
    assert (tmp_path / "state.json").read_text() == "{not json"
    assert not (tmp_path / "global.lock").exists(), "the lock is released after a refusal"


def test_the_lock_is_released_after_every_outcome(tmp_path):
    make(tmp_path, [row("r", "raise SystemExit(1)")]).run(dry_run=False)
    assert not (tmp_path / "global.lock").exists()


def test_the_state_file_is_written_atomically(tmp_path, monkeypatch):
    seen = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (seen.append((Path(a).name, Path(b).name)), real(a, b))[1])
    make(tmp_path, [row("r", "pass")]).run(dry_run=False)
    assert any(dst == "state.json" and src != "state.json" for src, dst in seen)


def test_the_log_has_no_environment_and_rows_with_secret_shaped_arguments_are_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("HCS_TICK_SECRET_PROBE", "leakvalue123")
    make(tmp_path, [row("r", "pass")]).run(dry_run=False)
    assert "leakvalue123" not in (tmp_path / "tick.log.jsonl").read_text()
    with pytest.raises(tick.RowError):
        tick.validate_rows([{"id": "x", "argv": ["tool", "--token=abc123def456"], "heavy": False}])
    with pytest.raises(tick.RowError):
        tick.validate_rows([{"id": "x", "argv": [], "heavy": False}])
    with pytest.raises(tick.RowError):
        tick.validate_rows([{"id": "dup", "argv": ["a"]}, {"id": "dup", "argv": ["b"]}])


def test_the_worker_does_not_inherit_the_callers_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HCS_TICK_SECRET_PROBE", "leakvalue123")
    out = tmp_path / "env.txt"
    code = f"import os; open({str(out)!r},'w').write(','.join(sorted(os.environ)))"
    assert make(tmp_path, [row("r", code)]).run(dry_run=False)["outcome"] == "ok"
    assert "HCS_TICK_SECRET_PROBE" not in out.read_text()


def test_the_default_state_dir_is_outside_the_repository():
    d = tick.default_state_dir()
    assert ROOT not in d.parents and d != ROOT
    assert d.name == "hscl-selfheal"
