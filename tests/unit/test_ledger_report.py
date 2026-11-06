"""scripts/ledger_report.py: the delegation ledger summary used at sprint boundaries (gate G38)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ledger_report.py"


def run(path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--path", str(path), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def write(tmp_path, *entries):
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(e) if isinstance(e, dict) else e for e in entries) + "\n", encoding="utf-8")
    return p


def test_counts_tools_outcomes_and_tokens(tmp_path):
    p = write(
        tmp_path,
        {"tool": "jev_noul", "job": "gate", "outcome": "OK", "tokens_est": 10},
        {"tool": "jev_noul", "job": "gate", "outcome": "WRONG (uncalibrated)", "tokens_est": 10},
        {"tool": "shell.grep", "job": "gate", "outcome": "OK", "tokens_est": 300},
    )
    r = run(p, "--json")
    assert r.returncode == 0, r.stderr
    s = json.loads(r.stdout)
    assert s["entries"] == 3
    assert s["tokens_est"] == 320
    assert s["by_tool"] == {"jev_noul": 2, "shell.grep": 1}
    assert s["by_outcome"] == {"OK": 2, "WRONG": 1}
    assert s["wrong"] == 1
    assert s["wrong_without_fallback"] == 0, "the same job was later done by a tool that succeeded"


def test_a_wrong_answer_without_fallback_fails_the_report(tmp_path):
    p = write(tmp_path, {"tool": "subagent.explore", "job": "inventory", "outcome": "WRONG", "tokens_est": 1})
    r = run(p)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "without fallback: 1" in r.stdout


def test_malformed_line_is_an_error_not_a_zero(tmp_path):
    p = write(tmp_path, {"tool": "a", "job": "j", "outcome": "OK"}, "{not json")
    r = run(p)
    assert r.returncode == 2
    assert "malformed" in r.stderr


def test_missing_ledger_is_an_error(tmp_path):
    r = run(tmp_path / "nope.jsonl")
    assert r.returncode == 2


def test_the_repository_ledger_parses():
    """The real ledger must stay machine-readable; a broken one hides delegation regressions."""
    ledger = ROOT / "artifacts/auto-loop/ledger.jsonl"
    if not ledger.exists():
        pytest.skip("no ledger committed in this checkout")
    r = run(ledger, "--json")
    assert r.returncode in (0, 3), r.stderr
    assert json.loads(r.stdout)["entries"] >= 1
