"""Plan L, Task L8: queue that hands `[local]` plan steps to the local worker and keeps the results as PROPOSALS only."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "local_worker"))
import local_queue  # noqa: E402
import loop  # noqa: E402
import round_log  # noqa: E402

SPEC = '{"files": ["impl.py"], "test_cmd": ["python", "check.py"], "protected": ["check.py"]}'
PLAN = f"""# Plan
- [x] [local] {SPEC} :: already done, must be ignored
- [ ] normal step without the tag
- [ ] [local] {SPEC} :: implement foo so that check.py passes
- [ ] [local] not-json :: broken spec
- [ ] [local] {{"files": ["../x.py"], "test_cmd": ["python", "c.py"]}} :: path escape
- [ ] [local] {{"files": ["impl.py"], "test_cmd": ["rm", "-rf", "/"]}} :: bad executable
"""


@pytest.fixture
def env(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "p.md").write_text(PLAN, encoding="utf-8")
    proj = tmp_path / "proj"
    proj.mkdir()
    return {"plans": plans, "proj": proj, "state": tmp_path / "state.json", "props": tmp_path / "proposals", "rounds": tmp_path / "rounds.jsonl"}


def run(env, run_task, gate=None, clock=None, max_items=5, wall=600, applies=lambda diff, root: True, dry=False):
    items = local_queue.parse_plans(env["plans"])
    return local_queue.run_queue(
        items, root=env["proj"], make_chat=lambda m: (lambda msgs: ""), run_task=run_task,
        gate=gate or (lambda m: {"ok": True, "reason": "ok"}), model="bonsai-9b", state_path=env["state"], proposals_dir=env["props"],
        rounds_path=env["rounds"], max_items=max_items, wall_seconds=wall, clock=clock or (lambda: 0.0), applies=applies, dry_run=dry,
    )


def green(*a, **k):
    return loop.Result(True, 1, "--- a/impl.py\n+++ b/impl.py\n+x = 1\n", "ok", "green")


def test_parse_finds_only_unchecked_tagged_steps_with_valid_json():
    items = local_queue.parse_plans_text("p.md", PLAN)
    tasks = [i.task for i in items if i.error is None]
    assert tasks == ["implement foo so that check.py passes", "path escape", "bad executable"]  # parse succeeds; validation is separate
    assert any(i.error for i in items if i.task == "broken spec")
    assert all(len(i.id) == 12 for i in items)
    assert len({i.id for i in items}) == len(items)


def test_invalid_items_are_reported_not_run(env):
    calls = []
    res = run(env, lambda *a, **k: calls.append(1) or green())
    by_task = {r["task"]: r for r in res["items"]}
    assert by_task["implement foo so that check.py passes"]["status"] == "proposed"
    assert by_task["path escape"]["status"] == "invalid" and by_task["bad executable"]["status"] == "invalid"
    assert by_task["broken spec"]["status"] == "invalid"
    assert len(calls) == 1


def test_a_green_result_is_written_as_a_diff_proposal_and_never_applied(env):
    res = run(env, green)
    item = next(r for r in res["items"] if r["status"] == "proposed")
    diff = Path(item["proposal"]).read_text(encoding="utf-8")
    assert "+x = 1" in diff and item["applies_cleanly"] is True
    assert list(env["proj"].iterdir()) == []  # the project tree was not touched


def test_a_red_result_is_recorded_without_a_proposal(env):
    res = run(env, lambda *a, **k: loop.Result(False, 3, "", "AssertionError", "max_rounds"))
    item = next(r for r in res["items"] if r["task"].startswith("implement foo"))
    assert item["status"] == "escalate" and item["proposal"] is None and item["reason"] == "max_rounds"


def test_finished_items_are_not_run_again(env):
    run(env, green)
    calls = []
    res = run(env, lambda *a, **k: calls.append(1) or green())
    assert not calls
    assert next(r for r in res["items"] if r["task"].startswith("implement foo"))["status"] == "already_done"


def test_closed_ram_gate_stops_the_queue_before_any_run(env):
    calls = []
    res = run(env, lambda *a, **k: calls.append(1) or green(), gate=lambda m: {"ok": False, "reason": "short by 2661 MiB"})
    assert not calls and res["stopped"] == "memory_gate: short by 2661 MiB"


def test_wall_clock_limit_stops_the_queue(env):
    ticks = iter([0.0, 0.0, 1000.0] + [1000.0] * 20)  # start, check before item 1, check before item 2
    calls = []
    res = run(env, lambda *a, **k: calls.append(1) or green(), clock=lambda: next(ticks), wall=100)
    assert res["stopped"] == "wall_clock" and len(calls) == 1


def test_max_items_is_respected(env):
    (env["plans"] / "q.md").write_text("\n".join(f"- [ ] [local] {SPEC} :: task number {i}" for i in range(6)), encoding="utf-8")
    calls = []
    run(env, lambda *a, **k: calls.append(1) or green(), max_items=2)
    assert len(calls) == 2


def test_every_run_is_recorded_with_the_round_log(env):
    run(env, green)
    rows = [json.loads(x) for x in env["rounds"].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["task"].startswith("queue:") and rows[0]["score"] == {"solved": 1, "rounds": 1}


def test_a_proposal_that_does_not_apply_cleanly_is_flagged(env):
    res = run(env, green, applies=lambda diff, root: False)
    assert next(r for r in res["items"] if r["status"] == "proposed")["applies_cleanly"] is False


def test_dry_run_lists_items_without_running_or_writing(env):
    calls = []
    res = run(env, lambda *a, **k: calls.append(1) or green(), dry=True)
    assert not calls and not env["state"].exists() and not env["props"].exists()
    assert any(r["status"] == "would_run" for r in res["items"])


def test_gateway_errors_stop_the_queue_with_the_code(env):
    import gateway

    def boom(*a, **k):
        raise gateway.GatewayError("unavailable", "refused")

    res = run(env, boom)
    assert res["stopped"] == "gateway_error: unavailable"


def test_next_round_helper_in_round_log(tmp_path):
    p = tmp_path / "r.jsonl"
    assert round_log.next_round(p, "t") == 1
    round_log.record_round("t", 1, {"a": 1}, "x", "y", p)
    round_log.record_round("t", 2, {"a": 1}, "x", "y", p)
    assert round_log.next_round(p, "t") == 3 and round_log.next_round(p, "other") == 1
