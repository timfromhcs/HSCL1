#!/usr/bin/env python3
"""Summarise `rounds.jsonl` per task (plan Track A2).

For each task: number of rounds, best round (first round that reached the best value), delta first-to-last, whether the last
round is worse than the first (`regressed`), and `stalled` = three or more rounds since the best value (the plan's stop rule:
write a BLOCKER instead of a fourth retry).

Exit codes: 0 = report written, 2 = malformed file, 3 = at least one task is stalled.
Usage: python scripts/round_report.py [--path FILE] [--key METRIC] [--lower-is-better] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT = Path("artifacts/auto-loop/rounds.jsonl")
STALL_AFTER = 3


def _load(path: Path) -> dict[str, list[dict]]:
    tasks: dict[str, list[dict]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            tasks.setdefault(row["task"], []).append(row)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"line {number}: {e}") from e
    return tasks


def summarise(path: Path, key: str, lower_is_better: bool = False) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for task, rows in _load(path).items():
        rows.sort(key=lambda r: r["round"])
        values = []
        for r in rows:
            if key not in r["score"]:
                out[task] = {"error": f"key '{key}' missing in round {r['round']}"}
                break
            values.append(r["score"][key])
        else:
            sign = -1 if lower_is_better else 1
            best_i = 0
            for i, v in enumerate(values):
                if sign * v > sign * values[best_i]:
                    best_i = i
            since_best = len(values) - 1 - best_i
            out[task] = {
                "rounds": len(values),
                "best_round": rows[best_i]["round"],
                "best_value": values[best_i],
                "delta_first_to_last": values[-1] - values[0],
                "regressed": sign * values[-1] < sign * values[0],
                "stalled": since_best >= STALL_AFTER,
            }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", type=Path, default=DEFAULT)
    ap.add_argument("--key", default="tests_passed")
    ap.add_argument("--lower-is-better", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        report = summarise(a.path, a.key, a.lower_is_better)
    except (ValueError, OSError) as e:
        print(f"round_report: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        for task, s in sorted(report.items()):
            if "error" in s:
                print(f"{task}: ERROR {s['error']}")
                continue
            flags = [f for f in ("stalled", "regressed") if s[f]]
            print(f"{task}: {s['rounds']} rounds, best round {s['best_round']} ({s['best_value']}), delta {s['delta_first_to_last']:+}"
                  + (f"  [{', '.join(flags)}]" if flags else ""))
    return 3 if any(s.get("stalled") for s in report.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
