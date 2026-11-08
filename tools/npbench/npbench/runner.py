"""Run a solver on an instance and report only what independent code backs.

* SAT is reported only if ``cnf.verify_model`` accepts the model; otherwise the verdict becomes UNKNOWN.
* UNSAT is reported only if an independent checker accepts the proof; otherwise the verdict becomes UNKNOWN.
  ``proof_checker`` names which one: ``rup`` (the CDCL baseline's own lemma format, no deletions) or ``drat``
  (DRAT lines, deletions, RUP per addition - RAT is not implemented, see :mod:`npbench.drat`). The record says
  which checker accepted, so a stronger label is never implied. An unknown name raises instead of falling back.
* A decided verdict that contradicts the instance's known answer is recorded as ``disagreement``.
* A solver that is not available is reported as ``unavailable``; there is no silent fallback to another solver.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Dict, Optional, Sequence

from . import gen_sat
from .cnf import Cnf, verify_model, write_dimacs
from .drat import check_drat
from .proof import check_rup
from .solvers import cdcl, walksat


class UnknownProofChecker(ValueError):
    """A checker that does not exist is refused; the run never falls back to one that does."""


def _certify_rup(formula: Cnf, proof: Optional[Sequence[Sequence[int]]]) -> bool:
    return check_rup(formula, proof)


def _certify_drat(formula: Cnf, proof: Optional[Sequence[Sequence[int]]]) -> bool:
    if proof is None:
        return False
    lines = []
    for clause in proof:
        lines.append(" ".join(str(x) for x in clause) + (" 0" if clause else "0"))
    return check_drat(formula, "\n".join(lines) + "\n").verdict == "unsat"


PROOF_CHECKERS: Dict[str, tuple[Callable[[Cnf, Any], bool], str]] = {
    "rup": (_certify_rup, "RUP_CHECKED"),
    "drat": (_certify_drat, "DRAT_RUP_CHECKED"),
}

SOLVERS: Dict[str, Callable[[Cnf, float, int], cdcl.Result]] = {
    "cdcl": lambda formula, budget_s, seed: cdcl.solve(formula, deadline_s=budget_s, seed=seed),
    "walksat": lambda formula, budget_s, seed: walksat.solve(formula, deadline_s=budget_s, seed=seed),
}


def run_instance(spec: Dict[str, Any], formula: Cnf, solver: str, *, budget_s: float, seed: int = 0,
                 proof_checker: str = "rup") -> Dict[str, Any]:
    if proof_checker not in PROOF_CHECKERS:
        raise UnknownProofChecker(
            f"unknown proof checker {proof_checker!r}; known: {', '.join(sorted(PROOF_CHECKERS))}"
        )
    certify, label = PROOF_CHECKERS[proof_checker]
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
        if certify(formula, result.proof):
            record.update(status="UNSAT", certification=label)
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
