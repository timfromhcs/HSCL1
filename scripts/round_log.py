#!/usr/bin/env python3
"""Round recorder for the propose-measure-reflect-revise loop (plan Track A1).

One JSON line per round in `artifacts/auto-loop/rounds.jsonl`: task, round number, a numeric score dict that comes from a
gate (tests, clippy, boot classifier ...), the action taken and a short reflection. Secrets and personal absolute paths are
refused, text is bounded, round numbers must increase per task, so the file can be summarised later by `round_report.py`.

Usage: python scripts/round_log.py TASK ROUND --score key=value [--score ...] --action TEXT --reflection TEXT [--path FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

DEFAULT = Path("artifacts/auto-loop/rounds.jsonl")
MAX_TEXT = 2000

SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[=:]\s*\S{6,}"),
]
PATH_PATTERNS = [
    re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+"),
    re.compile(r"/home/[^/\s]+"),
    re.compile(r"/Users/[^/\s]+"),
]


def _check_text(name: str, text: str) -> str:
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            raise ValueError(f"{name} looks like it contains a secret")
    for pat in PATH_PATTERNS:
        if pat.search(text):
            raise ValueError(f"{name} contains a personal absolute path")
    return text[:MAX_TEXT]


def _last_round(path: Path, task: str) -> int:
    last = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("task") == task:
                last = max(last, int(row.get("round", 0)))
    return last


def next_round(path: Path, task: str) -> int:
    """The round number to use next for this task (1 when the task is new)."""
    return _last_round(Path(path), task) + 1


def record_round(task: str, round_no: int, score: dict, action: str, reflection: str, path: Path = DEFAULT) -> dict:
    """Append one round; raises ValueError (nothing written) on secrets, paths, bad score or a non-increasing round."""
    task = _check_text("task", task)
    action = _check_text("action", action)
    reflection = _check_text("reflection", reflection)
    if not score or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in score.values()):
        raise ValueError("score must be a non-empty dict of numbers")
    if round_no < 1 or round_no <= _last_round(path, task):
        raise ValueError(f"round must increase per task (got {round_no})")
    row = {
        "task": task,
        "round": round_no,
        "score": score,
        "action": action,
        "reflection": reflection,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _parse_score(items: list[str]) -> dict:
    out = {}
    for item in items:
        key, sep, val = item.partition("=")
        if not sep:
            raise ValueError(f"--score needs key=value, got {item!r}")
        out[key] = float(val) if "." in val else int(val)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("task")
    ap.add_argument("round", type=int)
    ap.add_argument("--score", action="append", default=[])
    ap.add_argument("--action", required=True)
    ap.add_argument("--reflection", required=True)
    ap.add_argument("--path", type=Path, default=DEFAULT)
    a = ap.parse_args(argv)
    try:
        row = record_round(a.task, a.round, _parse_score(a.score), a.action, a.reflection, a.path)
    except ValueError as e:
        print(f"round_log: refused: {e}", file=sys.stderr)
        return 2
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
