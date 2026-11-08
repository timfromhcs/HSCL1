"""Run a TSP or knapsack solver on a decision task and report only what independent code backs.

Tasks: ``tsp bound`` (is there a tour of length <= bound) and ``knapsack target`` (is there a selection that fits and
reaches the profit target). Accepted evidence:

* yes: a tour that passes ``tsp.verify_tour`` with length <= bound, or a selection that passes ``knap.verify_selection``;
* no (TSP): integer potentials whose Lagrangian 1-tree bound, recomputed by ``tsp.lower_bound``, exceeds the bound;
* no (knapsack): the exact fractional bound, recomputed here by ``knap.fractional_upper_bound``, is below the target.

An exact dynamic programme that finishes without such a certificate is UNKNOWN, not a "no": the optimum it computed is
ground truth for the instance builder (validated against brute force in the tests) but not independent evidence.
"""

from __future__ import annotations

import time
from fractions import Fraction
from typing import Any, Callable, Dict, Optional

from . import knap_solvers as KS
from . import tsp_solvers as TS
from .knap import Knapsack, fractional_upper_bound, verify_selection
from .opt_types import OptResult
from .tsp import Tsp, lower_bound, verify_tour

OPT_SOLVERS: Dict[str, Dict[str, Callable[[Any, dict, float], OptResult]]] = {
    "tsp": {"dp": TS.solve_dp, "nn2opt": TS.solve_nn2opt, "lagrange": TS.solve_lagrange},
    "knapsack": {"dp": KS.solve_dp, "greedy": KS.solve_greedy, "ub": KS.solve_ub},
}


def _known_solver(name: str) -> bool:
    return any(name in solvers for solvers in OPT_SOLVERS.values())


def run_opt_instance(spec: Dict[str, Any], instance: Any, solver: str, *, budget_s: float, seed: int = 0) -> Optional[Dict[str, Any]]:
    task = spec["task"]
    kind = task["kind"]
    record: Dict[str, Any] = {
        "id": spec["id"], "family": spec["family"], "task": dict(task), "solver": solver, "expected": spec.get("expected"),
        "budget_s": float(budget_s), "elapsed_s": 0.0, "status": "UNKNOWN", "certification": "NONE", "conflicts": 0,
        "note": "", "disagreement": False,
    }
    run = OPT_SOLVERS.get(kind, {}).get(solver)
    if run is None:
        if _known_solver(solver):
            return None
        record.update(status="unavailable", note=f"solver {solver!r} is not available in this installation; no fallback was used")
        return record
    started = time.perf_counter()
    try:
        result = run(instance, task, budget_s)
    except Exception as exc:  # noqa: BLE001 - a solver failure is a recorded outcome
        record.update(elapsed_s=time.perf_counter() - started, status="error", note=type(exc).__name__)
        return record
    record["elapsed_s"] = time.perf_counter() - started
    record["conflicts"] = result.work
    record["note"] = result.note
    if result.status == "SAT":
        if _yes_ok(kind, instance, task, result):
            record.update(status="SAT", certification="WITNESS_VERIFIED")
        else:
            record.update(status="UNKNOWN", note="SAT claim refused: the witness does not pass the independent verifier")
    elif result.status == "UNSAT":
        certification = _no_ok(kind, instance, task, result)
        if certification:
            record.update(status="UNSAT", certification=certification)
        else:
            record.update(status="UNKNOWN", note="UNSAT claim refused: no certificate accepted by the independent checker")
    expected = spec.get("expected")
    record["disagreement"] = expected in ("SAT", "UNSAT") and record["status"] in ("SAT", "UNSAT") and record["status"] != expected
    return record


def _yes_ok(kind: str, instance: Any, task: dict, result: OptResult) -> bool:
    if kind == "tsp" and isinstance(instance, Tsp):
        length = verify_tour(instance, result.witness)
        return length is not None and length <= task["bound"]
    if kind == "knapsack" and isinstance(instance, Knapsack):
        return verify_selection(instance, result.witness, task["target"])
    return False


def _no_ok(kind: str, instance: Any, task: dict, result: OptResult) -> Optional[str]:
    if kind == "tsp" and isinstance(instance, Tsp) and result.cert_kind == "LOWER_BOUND":
        lb = lower_bound(instance, result.cert)
        return "LOWER_BOUND_VERIFIED" if lb is not None and lb > task["bound"] else None
    if kind == "knapsack" and isinstance(instance, Knapsack) and result.cert_kind == "LP_BOUND":
        return "LP_BOUND_VERIFIED" if Fraction(task["target"]) > fractional_upper_bound(instance) else None
    return None
