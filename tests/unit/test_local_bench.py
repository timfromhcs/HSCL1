"""Plan L, Task L7: benchmark harness and the ten tasks it runs. The tasks are themselves tested: the reference solution must
pass its check and a plausible-but-wrong solution must fail it, otherwise the benchmark would not discriminate."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import bench  # noqa: E402
import bench_tasks  # noqa: E402

TASKS = bench_tasks.TASKS


def run_check(tmp_path, task, impl):
    d = tmp_path / task["id"]
    d.mkdir()
    (d / "impl.py").write_text(impl, encoding="utf-8")
    (d / "check.py").write_text(task["check"], encoding="utf-8")
    return subprocess.run([sys.executable, "check.py"], cwd=d, capture_output=True, text=True, timeout=30)


def test_there_are_ten_tasks_with_unique_ids_and_complete_fields():
    assert len(TASKS) == 10 and len({t["id"] for t in TASKS}) == 10
    for t in TASKS:
        assert {"id", "prompt", "stub", "check", "reference", "naive"} <= set(t)
        assert re.fullmatch(r"[a-z0-9_]+", t["id"]) and len(t["prompt"]) > 40


def test_the_int_float_trap_is_one_of_the_tasks():
    assert any(t["id"] == "parse_score" for t in TASKS)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["id"])
def test_reference_passes_and_naive_fails(tmp_path, task):
    ok = run_check(tmp_path / "a", task, task["reference"]) if (tmp_path / "a").mkdir() is None else None
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = run_check(tmp_path / "b", task, task["naive"]) if (tmp_path / "b").mkdir() is None else None
    assert bad.returncode != 0, "the naive solution must be caught by the check"
    stub = run_check(tmp_path / "c", task, task["stub"]) if (tmp_path / "c").mkdir() is None else None
    assert stub.returncode != 0, "the unsolved stub must fail"


def make_chat_factory(solver):
    """solver(task) -> source; the fake model finds the task by its prompt text."""

    def factory(model):
        def chat(messages):
            user = messages[1]["content"]
            for t in TASKS:
                if t["prompt"] in user:
                    return f"FILE: impl.py\n```python\n{solver(t, model)}```\n"
            return ""

        return chat

    return factory


def test_perfect_model_solves_everything_in_round_one(tmp_path):
    r = bench.run_benchmark(["m1"], make_chat_factory(lambda t, m: t["reference"]), timeout_s=30)
    m = r["models"]["m1"]
    assert m["solved"] == 10 and m["pass_at_1"] == 10 and all(x["rounds"] == 1 for x in m["tasks"])


def test_naive_model_solves_nothing_and_uses_all_rounds(tmp_path):
    r = bench.run_benchmark(["m1"], make_chat_factory(lambda t, m: t["naive"]), max_rounds=2, timeout_s=30)
    m = r["models"]["m1"]
    assert m["solved"] == 0 and m["pass_at_1"] == 0 and all(x["rounds"] == 2 for x in m["tasks"])


def test_second_round_recovery_counts_as_solved_but_not_pass_at_1():
    calls = {}

    def solver(t, model):
        calls[t["id"]] = calls.get(t["id"], 0) + 1
        return t["naive"] if calls[t["id"]] == 1 else t["reference"]

    r = bench.run_benchmark(["m1"], make_chat_factory(solver), timeout_s=30)
    m = r["models"]["m1"]
    assert m["solved"] == 10 and m["pass_at_1"] == 0


def test_a_closed_memory_gate_skips_the_model_without_counting_failures():
    r = bench.run_benchmark(["big"], make_chat_factory(lambda t, m: t["reference"]), gate=lambda m: {"ok": False, "reason": "short by 2661 MiB"})
    assert r["models"]["big"] == {"skipped": "memory_gate: short by 2661 MiB"}


def test_two_models_are_reported_separately_and_a_gateway_error_is_recorded():
    import gateway

    def factory(model):
        if model == "down":
            def chat(messages):
                raise gateway.GatewayError("unavailable", "refused")
            return chat
        return make_chat_factory(lambda t, m: t["reference"])(model)

    r = bench.run_benchmark(["ok", "down"], factory, timeout_s=30, max_rounds=1)
    assert r["models"]["ok"]["solved"] == 10
    assert r["models"]["down"]["error"] == "gateway_error: unavailable" and "solved" not in r["models"]["down"]


def test_summary_table_is_markdown_with_one_row_per_model():
    r = bench.run_benchmark(["m1"], make_chat_factory(lambda t, m: t["reference"]), timeout_s=30)
    md = bench.render_markdown(r)
    assert md.count("\n| m1 ") == 1 and "10/10" in md


def test_cli_without_a_reachable_gateway_exits_cleanly(tmp_path, capsys):
    rc = bench.main(["--models", "nope", "--out", str(tmp_path), "--gateway", "http://127.0.0.1:9/v1", "--no-gate", "--rounds", "1", "--limit", "1"])
    out = capsys.readouterr().out
    assert rc == 0 and "gateway_error: unavailable" in out
    assert list(tmp_path.glob("bench-tasks-*.json"))


def test_history_mode_is_passed_to_the_loop_and_recorded(monkeypatch):
    seen = []
    real = bench.loop.run_task

    def spy(*a, **k):
        seen.append(k.get("history"))
        return real(*a, **k)

    monkeypatch.setattr(bench.loop, "run_task", spy)
    r = bench.run_benchmark(["m1"], make_chat_factory(lambda t, m: t["reference"]), timeout_s=30, limit=2, history="full")
    assert seen == ["full", "full"] and r["history"] == "full"
    r2 = bench.run_benchmark(["m1"], make_chat_factory(lambda t, m: t["reference"]), timeout_s=30, limit=1)
    assert r2["history"] == "window" and seen[-1] == "window"


def test_cli_accepts_history_option(tmp_path):
    rc = bench.main(["--models", "nope", "--out", str(tmp_path), "--gateway", "http://127.0.0.1:9/v1", "--no-gate", "--rounds", "1", "--limit", "1", "--history", "full"])
    assert rc == 0
    import json as _json

    data = _json.loads(next(tmp_path.glob("bench-tasks-*.json")).read_text(encoding="utf-8"))
    assert data["history"] == "full"
