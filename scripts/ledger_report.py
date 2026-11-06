#!/usr/bin/env python3
"""Summarise the delegation ledger (plan Track A, gate G38).

Every delegated call (OpenJev, subagent, MCP) appends one JSON line to
`artifacts/auto-loop/ledger.jsonl`. This script answers the only question that matters at a sprint
boundary: was delegation worth it, and did any delegated answer turn out to be wrong?

Exit codes: 0 = report written, 2 = malformed ledger line, 3 = wrong answers without a fallback.

Usage:
    python scripts/ledger_report.py [--path FILE] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DEFAULT = Path("artifacts/auto-loop/ledger.jsonl")
BAD_OUTCOME = "WRONG"


def load(path: Path) -> tuple[list[dict], list[int]]:
    entries: list[dict] = []
    bad: list[int] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad.append(number)
            continue
        if not isinstance(obj, dict) or "tool" not in obj or "outcome" not in obj:
            bad.append(number)
            continue
        entries.append(obj)
    return entries, bad


def summarise(entries: list[dict]) -> dict:
    tools = Counter(e["tool"] for e in entries)
    kinds = Counter(str(e["outcome"]).split(" ")[0].upper() for e in entries)
    tokens = sum(int(e.get("tokens_est") or 0) for e in entries)
    wrong = [e for e in entries if str(e["outcome"]).upper().startswith(BAD_OUTCOME)]
    return {
        "entries": len(entries),
        "tokens_est": tokens,
        "by_tool": dict(sorted(tools.items())),
        "by_outcome": dict(sorted(kinds.items())),
        "wrong": len(wrong),
        # a wrong delegated answer is only acceptable if the same job was done again by another tool
        "wrong_without_fallback": sum(
            1
            for e in wrong
            if not any(
                o is not e and o.get("job") == e.get("job") and str(o["outcome"]).upper().startswith("OK")
                for o in entries
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.path.exists():
        print(f"ledger_report: no ledger at {args.path}", file=sys.stderr)
        return 2
    entries, bad = load(args.path)
    if bad:
        print(f"ledger_report: malformed line(s): {bad}", file=sys.stderr)
        return 2
    summary = summarise(entries)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"entries: {summary['entries']}  est. tokens: {summary['tokens_est']}")
        for tool, count in summary["by_tool"].items():
            print(f"  {count:3d}  {tool}")
        print("outcomes: " + ", ".join(f"{k}={v}" for k, v in summary["by_outcome"].items()))
        if summary["wrong"]:
            print(f"wrong answers: {summary['wrong']} (without fallback: {summary['wrong_without_fallback']})")
    return 3 if summary["wrong_without_fallback"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
