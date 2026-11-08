"""Read-only probe for the CQ-HECS Python DIMACS parser (audit finding P1).

Runs in a *separate* interpreter, because ``cqhecs.sat`` needs qiskit and therefore cannot be imported into the
gate's Python 3.14 venv. Input: a JSON list of ``{"id", "text"}`` on stdin. Output: one JSON object per case on
stdout. It never writes to the clone and never imports anything from this repository.

Usage (from the WSL lab):
    ~/venvs/cq/bin/python tests/helpers/cqhecs_parser_probe.py < cases.json

Environment: ``HSCL1_CQHECS_CLONE`` (default ``/home/tim/src/CQ-HECS``).
"""
from __future__ import annotations

import json
import os
import sys

CLONE = os.environ.get("HSCL1_CQHECS_CLONE", "/home/tim/src/CQ-HECS")


def main() -> int:
    sys.path.insert(0, CLONE)
    try:
        from cqhecs.sat import parse_dimacs  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        print(json.dumps({"probe": "import_failed", "error": f"{type(exc).__name__}: {exc}"}))
        return 0
    print(json.dumps({"probe": "ok", "module": parse_dimacs.__module__}))
    cases = json.load(sys.stdin)
    for case in cases:
        try:
            result = parse_dimacs(case["text"])
            clauses = tuple(tuple(int(x) for x in clause) for clause in (getattr(result, "clauses", ()) or ()))
            answer = {"id": case["id"], "outcome": "accept", "num_vars": int(getattr(result, "num_vars", -1)),
                      "clauses": [list(c) for c in clauses]}
        except Exception as exc:  # noqa: BLE001 - a refusal is the observation
            answer = {"id": case["id"], "outcome": "reject", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
