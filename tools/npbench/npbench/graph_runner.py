"""Run a graph-task solver and report only what independent code backs (same rules as ``runner`` for SAT).

Tasks (decision problems): ``coloring k`` (is the graph k-colourable), ``clique k`` (is there a clique of size k),
``hamcycle`` (is there a Hamiltonian cycle). Evidence accepted by the runner:

* yes-answers: the witness (colouring, clique, vertex order) passes the verifier in ``graph``;
* no-answers: for ``coloring`` and ``hamcycle`` a RUP proof of the encoding, re-built here from the graph and checked by
  ``proof.check_rup``; for ``clique k`` a proper colouring with k-1 colours (it proves no k-clique exists).

Anything else becomes UNKNOWN. A (solver, task) pair that does not exist is skipped; a solver name that exists for no
task is reported as ``unavailable``.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from . import graph_solvers as GS
from .graph import Graph, verify_clique, verify_coloring, verify_ham_cycle
from .proof import check_rup


def _clique_bk(g: Graph, k: Optional[int], deadline_s: float) -> GS.GraphResult:
    started = time.perf_counter()
    found = GS.max_clique(g, deadline_s=deadline_s)
    if k is not None and found.witness and len(found.witness) >= k:
        return GS.GraphResult("SAT", found.witness, None, None, found.work, found.note)
    if not found.complete or k is None or k < 2:
        return GS.GraphResult("UNKNOWN", None, None, None, found.work, "no clique of the size found before the deadline")
    remaining = max(0.1, deadline_s - (time.perf_counter() - started))
    for attempt in (GS.dsatur, GS.sat_coloring):
        res = attempt(g, k - 1, remaining)
        if res.status == "SAT":
            return GS.GraphResult("UNSAT", None, "COLORING_BOUND", res.witness, found.work, "search complete; bound by a colouring")
    return GS.GraphResult("UNKNOWN", None, None, None, found.work, "search complete but no independent certificate was found")


GRAPH_SOLVERS: Dict[str, Dict[str, Callable[[Graph, Optional[int], float], GS.GraphResult]]] = {
    "coloring": {
        "sat": lambda g, k, deadline_s: GS.sat_coloring(g, k, deadline_s),
        "dsatur": lambda g, k, deadline_s: GS.dsatur(g, k, deadline_s),
    },
    "clique": {"bk": _clique_bk},
    "hamcycle": {
        "sat": lambda g, k, deadline_s: GS.sat_ham(g, deadline_s),
        "backtrack": lambda g, k, deadline_s: GS.ham_backtrack(g, deadline_s),
    },
}


def _known_solver(name: str) -> bool:
    return any(name in solvers for solvers in GRAPH_SOLVERS.values())


def run_graph_instance(spec: Dict[str, Any], g: Graph, solver: str, *, budget_s: float, seed: int = 0) -> Optional[Dict[str, Any]]:
    task = spec["task"]
    kind, k = task["kind"], task.get("k")
    record: Dict[str, Any] = {
        "id": spec["id"], "family": spec["family"], "task": dict(task), "solver": solver, "expected": spec.get("expected"),
        "budget_s": float(budget_s), "elapsed_s": 0.0, "status": "UNKNOWN", "certification": "NONE", "conflicts": 0,
        "note": "", "disagreement": False,
    }
    registry = GRAPH_SOLVERS.get(kind, {})
    run = registry.get(solver)
    if run is None:
        if _known_solver(solver):
            return None  # the solver exists, just not for this task
        record.update(status="unavailable", note=f"solver {solver!r} is not available in this installation; no fallback was used")
        return record
    started = time.perf_counter()
    try:
        result = run(g, k, budget_s)
    except Exception as exc:  # noqa: BLE001 - a solver failure is a recorded outcome
        record.update(elapsed_s=time.perf_counter() - started, status="error", note=type(exc).__name__)
        return record
    record["elapsed_s"] = time.perf_counter() - started
    record["conflicts"] = result.work
    record["note"] = result.note
    if result.status == "SAT":
        if _witness_ok(kind, g, k, result.witness):
            record.update(status="SAT", certification="WITNESS_VERIFIED")
        else:
            record.update(status="UNKNOWN", note="SAT claim refused: the witness does not pass the independent verifier")
    elif result.status == "UNSAT":
        certification = _no_certificate_ok(kind, g, k, result)
        if certification:
            record.update(status="UNSAT", certification=certification)
        else:
            record.update(status="UNKNOWN", note="UNSAT claim refused: no certificate accepted by the independent checker")
    expected = spec.get("expected")
    record["disagreement"] = expected in ("SAT", "UNSAT") and record["status"] in ("SAT", "UNSAT") and record["status"] != expected
    return record


def _witness_ok(kind: str, g: Graph, k: Optional[int], witness: Any) -> bool:
    if witness is None:
        return False
    if kind == "coloring":
        return k is not None and k >= 1 and verify_coloring(g, witness, k)
    if kind == "clique":
        return k is not None and verify_clique(g, witness, k)
    if kind == "hamcycle":
        return verify_ham_cycle(g, witness)
    return False


def _no_certificate_ok(kind: str, g: Graph, k: Optional[int], result: GS.GraphResult) -> Optional[str]:
    if kind == "coloring" and result.cert_kind == "RUP" and k is not None and k >= 1:
        return "RUP_CHECKED" if check_rup(GS.coloring_cnf(g, k), result.cert) else None
    if kind == "hamcycle" and result.cert_kind == "RUP":
        return "RUP_CHECKED" if check_rup(GS.ham_cnf(g), result.cert) else None
    if kind == "clique" and result.cert_kind == "COLORING_BOUND" and k is not None and k >= 2:
        return "COLORING_BOUND_VERIFIED" if result.cert is not None and verify_coloring(g, result.cert, k - 1) else None
    return None
