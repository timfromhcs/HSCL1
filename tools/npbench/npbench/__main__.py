"""Command line: ``python -m npbench run|list|manifest``.

Exit codes: 0 all fine; 1 at least one disagreement, refused claim, error or unavailable solver; 2 usage error or
refusal to overwrite/run (bad suite, bad budget, existing report without ``--force``, heavy suite without
``--allow-heavy``). A timeout (UNKNOWN) is a normal benchmark outcome and does not fail the run.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from . import graph_runner, opt_runner, runner, suites as S

SCHEMA = "npbench.report.v1"
MAX_BUDGET_S = 3600.0


def _summary(records: List[Dict[str, Any]], solver: str) -> Dict[str, Any]:
    own = [r for r in records if r["solver"] == solver]
    return {
        "instances": len(own),
        "decided": sum(r["status"] in ("SAT", "UNSAT") for r in own),
        "sat": sum(r["status"] == "SAT" for r in own),
        "unsat": sum(r["status"] == "UNSAT" for r in own),
        "unknown": sum(r["status"] == "UNKNOWN" for r in own),
        "unavailable": sum(r["status"] == "unavailable" for r in own),
        "errors": sum(r["status"] == "error" for r in own),
        "refused": sum("claim refused" in r["note"] for r in own),
        "disagreements": sum(bool(r["disagreement"]) for r in own),
        "par2": runner.par2(own),
    }


def _run(args: argparse.Namespace) -> int:
    try:
        specs = S.suite_specs(args.suite)
    except ValueError as exc:
        print(f"npbench: {exc}", file=sys.stderr)
        return 2
    if S.is_heavy(args.suite) and not args.allow_heavy:
        print(f"npbench: suite {args.suite!r} is heavy; pass --allow-heavy to run it", file=sys.stderr)
        return 2
    if not math.isfinite(args.budget) or not 0 < args.budget <= MAX_BUDGET_S:
        print(f"npbench: --budget must be in (0, {MAX_BUDGET_S:g}] seconds", file=sys.stderr)
        return 2
    out = Path(args.out)
    if out.exists() and not args.force:
        print(f"npbench: {out} exists; pass --force to replace it", file=sys.stderr)
        return 2
    solvers = [s.strip() for s in args.solvers.split(",") if s.strip()]
    if not solvers:
        print("npbench: no solver given", file=sys.stderr)
        return 2
    records: List[Dict[str, Any]] = []
    for spec in specs:
        if spec["family"] in S.OPT_FAMILIES:
            instance, truth = S.build_opt_instance(spec)
            for solver in solvers:
                rec = opt_runner.run_opt_instance({**spec, "expected": truth}, instance, solver, budget_s=args.budget, seed=args.seed)
                if rec is not None:
                    records.append(rec)
            continue
        if spec["family"] in S.GRAPH_FAMILIES:
            graph, truth = S.build_graph_instance(spec)
            for solver in solvers:
                rec = graph_runner.run_graph_instance({**spec, "expected": truth}, graph, solver, budget_s=args.budget, seed=args.seed)
                if rec is not None:  # None: this solver exists, but not for this task
                    records.append(rec)
            continue
        formula, truth = S.build_instance(spec)
        for solver in solvers:
            records.append(runner.run_instance({"id": spec["id"], "family": spec["family"], "expected": truth}, formula, solver,
                                               budget_s=args.budget, seed=args.seed))
    report = {
        "schema": SCHEMA, "suite": args.suite, "solvers": solvers, "budget_s": args.budget, "seed": args.seed,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": platform.python_version(), "platform": platform.platform(),
        "manifest": S.manifest(args.suite), "records": records,
        "summary": {s: _summary(records, s) for s in solvers},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    for s in solvers:
        sm = report["summary"][s]
        par2 = "n/a" if sm["par2"] is None else f"{sm['par2']:.3f}"
        print(f"{s}: decided {sm['decided']}/{sm['instances']} (SAT {sm['sat']}, UNSAT {sm['unsat']}), PAR-2 {par2} s, "
              f"disagreements {sm['disagreements']}, refused {sm['refused']}, unavailable {sm['unavailable']}")
    print(f"report: {out}")
    bad = any(sm["disagreements"] or sm["refused"] or sm["errors"] or sm["unavailable"] for sm in report["summary"].values())
    return 1 if bad else 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="npbench", description="NP benchmark harness (slice 1: SAT)")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run solvers on a suite and write a JSON report")
    run.add_argument("--suite", default="light")
    run.add_argument("--solvers", default="cdcl")
    run.add_argument("--budget", type=float, default=10.0, help="seconds per solver and instance")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out", default=None, help="report path (default artifacts/npbench/<suite>.json)")
    run.add_argument("--force", action="store_true")
    run.add_argument("--allow-heavy", action="store_true")
    sub.add_parser("list", help="list the suites")
    man = sub.add_parser("manifest", help="print the manifest of a suite")
    man.add_argument("--suite", default="light")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    if args.command == "list":
        for name in S.suite_names():
            print(f"{name}\t{len(S.suite_specs(name))} instances\t{'heavy' if S.is_heavy(name) else 'light'}")
        return 0
    if args.command == "manifest":
        try:
            print(json.dumps(S.manifest(args.suite), indent=2, sort_keys=True))
        except ValueError as exc:
            print(f"npbench: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.out is None:
        args.out = str(Path("artifacts") / "npbench" / f"{args.suite}.json")
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
