"""Track A2: summarise rounds per task: best round, first-to-last delta, and the 3-stalled-rounds stop rule."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import round_report  # noqa: E402


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def row(task, n, **score):
    return {"task": task, "round": n, "score": score, "action": "a", "reflection": "r", "ts": "2026-11-06T00:00:00Z"}


def test_improving_task(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, passed=5), row("t", 2, passed=8), row("t", 3, passed=12)])
    s = round_report.summarise(p, key="passed")["t"]
    assert s["best_round"] == 3 and s["delta_first_to_last"] == 7 and s["stalled"] is False and s["rounds"] == 3


def test_three_rounds_without_a_new_best_is_stalled(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, passed=5), row("t", 2, passed=9), row("t", 3, passed=9), row("t", 4, passed=8), row("t", 5, passed=9)])
    s = round_report.summarise(p, key="passed")["t"]
    assert s["best_round"] == 2 and s["stalled"] is True


def test_two_rounds_since_the_best_are_not_yet_stalled(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, passed=5), row("t", 2, passed=9), row("t", 3, passed=9), row("t", 4, passed=9)])
    assert round_report.summarise(p, key="passed")["t"]["stalled"] is False  # best at 2, two rounds since
    write(p, [row("t", 1, passed=5), row("t", 2, passed=9), row("t", 3, passed=9), row("t", 4, passed=9), row("t", 5, passed=9)])
    assert round_report.summarise(p, key="passed")["t"]["stalled"] is True  # three rounds since the best


def test_lower_is_better_metric(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, warnings=9), row("t", 2, warnings=2), row("t", 3, warnings=4)])
    s = round_report.summarise(p, key="warnings", lower_is_better=True)["t"]
    assert s["best_round"] == 2 and s["delta_first_to_last"] == -5


def test_regression_is_visible(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, passed=10), row("t", 2, passed=7)])
    assert round_report.summarise(p, key="passed")["t"]["regressed"] is True


def test_tasks_are_separate_and_missing_key_is_reported(tmp_path):
    p = tmp_path / "r.jsonl"
    write(p, [row("a", 1, passed=1), row("b", 1, other=1)])
    out = round_report.summarise(p, key="passed")
    assert "a" in out and out["b"]["error"] == "key 'passed' missing in round 1"


def test_malformed_line_raises(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        round_report.summarise(p, key="passed")


def test_cli_exit_code_is_3_when_a_task_is_stalled(tmp_path, capsys):
    p = tmp_path / "r.jsonl"
    write(p, [row("t", 1, passed=9), row("t", 2, passed=9), row("t", 3, passed=9), row("t", 4, passed=9)])
    assert round_report.main(["--path", str(p), "--key", "passed"]) == 3
    assert "stalled" in capsys.readouterr().out
