"""Run a solver on an instance and report only what independent code backs.

* SAT is reported only if ``cnf.verify_model`` accepts the model; otherwise the verdict becomes UNKNOWN.
* UNSAT is reported only if ``proof.check_rup`` accepts the proof; otherwise the verdict becomes UNKNOWN.
* A decided verdict that contradicts the instance's known answer is recorded as ``disagreement``.
* A solver that is not available is reported as ``unavailable``; there is no silent fallback to another solver.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Dict, Optional, Sequence

from . import gen_sat
from .cnf import Cnf, verify_model, write_dimacs
from .proof import check_rup
from .solvers import cdcl, walksat

SOLVERS: Dict[str, Callable[[Cnf, float, int], cdcl.Result]] = {
    "cdcl": lambda formula, budget_s, seed: cdcl.solve(formula, deadline_s=budget_s, seed=seed),
    "walksat": lambda formula, budget_s, seed: walksat.solve(formula, deadline_s=budget_s, seed=seed),
}


def run_instance(spec: Dict[str, Any], formula: Cnf, solver: str, *, budget_s: float, seed: int = 0) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "id": spec["id"], "family": spec["family"], "solver": solver, "expected": spec.get("expected"),
        "budget_s": float(budget_s), "elapsed_s": 0.0, "status": "UNKNOWN", "certification": "NONE",
        "conflicts": 0, "note": "", "disagreement": False,
    }
    run = SOLVERS.get(solver)
    if run is None:
        record.update(status="unavailable", note=f"solver {solver!r} is not available in this installation; no fallback was used")
        return record
    started = time.perf_counter()
    try:
        result = run(formula, budget_s, seed)
    except Exception as exc:  # noqa: BLE001 - a solver failure is a recorded outcome
        record.update(elapsed_s=time.perf_counter() - started, status="error", note=f"{type(exc).__name__}")
        return record
    record["elapsed_s"] = time.perf_counter() - started
    record["conflicts"] = result.conflicts
    record["note"] = result.note
    if result.status == "SAT":
        if result.model is not None and verify_model(formula, result.model):
            record.update(status="SAT", certification="MODEL_VERIFIED")
        else:
            record.update(status="UNKNOWN", note="SAT claim refused: the model does not satisfy the formula")
    elif result.status == "UNSAT":
        if check_rup(formula, result.proof):
            record.update(status="UNSAT", certification="RUP_CHECKED")
        else:
            record.update(status="UNKNOWN", note="UNSAT claim refused: the proof was not accepted by the independent checker")
    expected = spec.get("expected")
    record["disagreement"] = expected in ("SAT", "UNSAT") and record["status"] in ("SAT", "UNSAT") and record["status"] != expected
    return record


def par2(records: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Penalised average runtime as in the SAT Competition: an undecided run counts twice its budget."""
    if not records:
        return None
    total = 0.0
    for rec in records:
        total += rec["elapsed_s"] if rec["status"] in ("SAT", "UNSAT") else 2.0 * rec["budget_s"]
    return total / len(records)


def manifest_entry(instance_id: str, family: str, params: Dict[str, Any], formula: Cnf, *, expected: Optional[str]) -> Dict[str, Any]:
    return {
        "id": instance_id, "family": family, "params": dict(params), "expected": expected,
        "generator": gen_sat.GENERATOR_VERSION,
        "num_vars": formula.num_vars, "num_clauses": len(formula.clauses),
        "sha256": hashlib.sha256(write_dimacs(formula).encode("ascii")).hexdigest(),
    }
