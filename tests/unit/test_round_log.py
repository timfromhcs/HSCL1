"""Track A1: the round recorder keeps a verifiable score per round and refuses secrets and personal paths."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import round_log  # noqa: E402


def rec(path, task="t", n=1, score=None, action="a", reflection="r"):
    return round_log.record_round(task, n, score if score is not None else {"tests_passed": 1}, action, reflection, path)


def test_appends_one_valid_json_line_per_round(tmp_path):
    p = tmp_path / "rounds.jsonl"
    rec(p, n=1, score={"tests_passed": 10, "clippy_warnings": 3})
    rec(p, n=2, score={"tests_passed": 12, "clippy_warnings": 0})
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert set(first) == {"task", "round", "score", "action", "reflection", "ts"}
    assert first["round"] == 1 and first["score"]["clippy_warnings"] == 3


def test_round_numbers_must_increase_per_task(tmp_path):
    p = tmp_path / "rounds.jsonl"
    rec(p, task="a", n=1)
    rec(p, task="b", n=1)  # other task, fine
    with pytest.raises(ValueError, match="round"):
        rec(p, task="a", n=1)
    with pytest.raises(ValueError, match="round"):
        rec(p, task="a", n=0)


@pytest.mark.parametrize(
    "text",
    [
        "token ghp_" + "a" * 36,
        "key sk-" + "b" * 32,
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "Authorization: Bearer " + "c" * 30,
        "password=hunter2hunter2",
    ],
)
def test_secrets_are_refused_in_every_text_field(tmp_path, text):
    p = tmp_path / "rounds.jsonl"
    with pytest.raises(ValueError, match="secret"):
        rec(p, reflection=text)
    with pytest.raises(ValueError, match="secret"):
        rec(p, action=text)
    assert not p.exists() or p.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize("text", [r"see C:\Users\alice\notes.txt", "open /home/alice/.ssh/id_rsa", "in /Users/bob/x"])
def test_personal_absolute_paths_are_refused(tmp_path, text):
    with pytest.raises(ValueError, match="path"):
        rec(tmp_path / "rounds.jsonl", action=text)


def test_score_values_must_be_numbers(tmp_path):
    with pytest.raises(ValueError, match="score"):
        rec(tmp_path / "rounds.jsonl", score={"tests_passed": "many"})
    with pytest.raises(ValueError, match="score"):
        rec(tmp_path / "rounds.jsonl", score={})


def test_text_is_bounded(tmp_path):
    p = tmp_path / "rounds.jsonl"
    rec(p, reflection="x" * 50000)
    assert len(json.loads(p.read_text(encoding="utf-8"))["reflection"]) <= 2000
