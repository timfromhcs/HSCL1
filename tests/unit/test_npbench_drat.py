"""NP benchmark, slice 5a: DRAT line format, deletion-aware RUP checking, and the honest RAT boundary.

The point of these tests is not that a proof is accepted - it is that a proof which is *not* checkable is
never reported as a refutation. Two of them exist only to catch a checker that quietly accepts everything.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import cnf as C  # noqa: E402
from npbench import drat as D  # noqa: E402
from npbench import gen_sat as G  # noqa: E402
from npbench import runner as R  # noqa: E402
from npbench.solvers import cdcl  # noqa: E402


def drat_text(proof) -> str:
    """Write a lemma list in the DRAT line format (clause, then 0)."""
    out = []
    for clause in proof:
        out.append(" ".join(str(x) for x in clause) + (" 0" if clause else "0"))
    return "\n".join(out) + "\n"


# a formula whose refutation needs exactly one unit propagation chain
CHAIN = C.parse_dimacs("p cnf 3 3\n1 0\n2 0\n-1 -2 0\n")
CHAIN_PROOF = "0\n"

# (1 or 2) with (1 or not 2) forces 1; adding "1" is RUP, the empty clause is not yet justified
FORCES_ONE = C.parse_dimacs("p cnf 2 2\n1 2 0\n1 -2 0\n")


# ---------------------------------------------------------------- accepts real proofs
def test_accepts_the_cdcl_baseline_proofs():
    checked = 0
    for seed in range(1, 41):
        formula = G.threshold_instance(6, seed=seed)
        result = cdcl.solve(formula, deadline_s=5.0, seed=seed)
        if result.status != "UNSAT":
            continue
        verdict = D.check_drat(formula, drat_text(result.proof))
        assert verdict.verdict == D.UNSAT, (seed, verdict)
        assert verdict.reason == D.CHECKED and verdict.line
        checked += 1
    assert checked >= 5, f"only {checked} UNSAT instances in 40 threshold instances; the test would be weak"


def test_hand_written_refutation_is_accepted():
    verdict = D.check_drat(CHAIN, "c a two-step chain\n1 0\n2 0\n-1 -2 0\n0\n")
    assert verdict.verdict == D.UNSAT and verdict.reason == D.CHECKED


def test_a_formula_with_the_empty_clause_is_refuted_without_a_proof():
    formula = C.Cnf(1, ((), (1,)))
    verdict = D.check_drat(formula, "")
    assert verdict.verdict == D.UNSAT
    assert "itself contains the empty clause" in verdict.detail


def test_comment_lines_and_padding_are_ignored():
    text = "c header\nc\n  -1   -2   0  \n0\n"
    verdict = D.check_drat(CHAIN, text)
    assert verdict.verdict == D.UNSAT


# ---------------------------------------------------------------- deletions must really delete
def test_deletion_removes_the_clause_it_names():
    # Without the deletion the refutation is valid ...
    assert D.check_drat(CHAIN, "0\n").verdict == D.UNSAT
    # ... and with it, the propagation chain that produced the conflict is gone.
    verdict = D.check_drat(CHAIN, "d 2 0\n0\n")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.INVALID_STEP
    assert verdict.line == 2 and verdict.deletions == 1


def test_deleting_an_absent_clause_is_counted_not_fatal():
    verdict = D.check_drat(CHAIN, "d 3 0\n0\n")
    assert verdict.verdict == D.UNSAT
    assert verdict.deletions == 1 and verdict.deletions_not_found == 1


def test_deletion_by_content_hits_the_first_live_copy():
    formula = C.parse_dimacs("p cnf 2 4\n1 2 0\n1 2 0\n-1 0\n-2 0\n")
    # Two copies of (1 2) are alive, so the refutation works ...
    assert D.check_drat(formula, "0\n").verdict == D.UNSAT
    # ... one deletion leaves the second copy, so it still works ...
    assert D.check_drat(formula, "d 1 2 0\n0\n").verdict == D.UNSAT
    # ... and after both are gone the conflict that made the empty clause RUP is gone too.
    verdict = D.check_drat(formula, "d 1 2 0\nd 1 2 0\n0\n")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.INVALID_STEP
    assert verdict.deletions == 2 and verdict.deletions_not_found == 0


# ---------------------------------------------------------------- the RAT boundary
def test_a_step_that_is_not_rup_is_reported_as_rat_unsupported():
    verdict = D.check_drat(FORCES_ONE, "2 0\n0\n")
    assert verdict.verdict == D.UNKNOWN
    assert verdict.reason == D.RAT_UNSUPPORTED and verdict.line == 1
    assert "RAT is not implemented" in verdict.detail


def test_an_empty_clause_that_is_not_rup_is_an_invalid_step_not_a_refutation():
    verdict = D.check_drat(FORCES_ONE, "0\n")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.INVALID_STEP


def test_a_proof_for_another_formula_is_never_accepted():
    other = C.parse_dimacs("p cnf 3 1\n1 2 3 0\n")
    verdict = D.check_drat(other, "0\n")
    assert verdict.verdict == D.UNKNOWN


def test_a_proof_without_the_empty_clause_is_incomplete():
    verdict = D.check_drat(FORCES_ONE, "1 0\n")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.INCOMPLETE_PROOF
    assert verdict.additions == 1 and verdict.steps == 1


def test_an_empty_proof_is_incomplete_not_a_refutation():
    verdict = D.check_drat(FORCES_ONE, "")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.INCOMPLETE_PROOF


def test_the_verdict_object_is_truthy_only_for_unsat():
    assert bool(D.check_drat(CHAIN, "0\n")) is True
    assert bool(D.check_drat(FORCES_ONE, "0\n")) is False


# ---------------------------------------------------------------- strict format
@pytest.mark.parametrize("text,why", [
    ("1.0 0\n", "float token"),
    ("+1 0\n", "plus sign"),
    ("1 0 2 0\n", "two clauses on one line"),
    ("1 0 2\n", "second clause unterminated"),
    ("1\n", "missing terminator"),
    ("d\n", "'d' without a clause"),
    ("1 9 0\n", "literal above the declared variables"),
    ("1 _ 0\n", "non-integer token"),
    ("1 0\n\n2 0\n", "blank line inside the proof"),
])
def test_drat_format_is_strict(text, why):
    with pytest.raises(D.DratFormatError):
        D.parse_drat(text, num_vars=3)


def test_a_malformed_proof_is_reported_as_malformed_not_as_unknown_format_error():
    verdict = D.check_drat(FORCES_ONE, "1.0 0\n")
    assert verdict.verdict == D.UNKNOWN and verdict.reason == D.MALFORMED
    assert verdict.line == 1 and "bad token" in verdict.detail


def test_the_byte_cap_is_checked_before_parsing(monkeypatch):
    monkeypatch.setattr(D, "MAX_PROOF_BYTES", 8)
    with pytest.raises(D.DratFormatError):
        D.parse_drat("1 0\n2 0\n3 0\n", num_vars=3)


def test_the_step_cap_is_checked_during_parsing(monkeypatch):
    monkeypatch.setattr(D, "MAX_STEPS", 1)
    with pytest.raises(D.DratFormatError):
        D.parse_drat("1 0\n2 0\n", num_vars=2)


def test_the_parse_result_keeps_line_numbers_and_deletion_flags():
    steps = D.parse_drat("c x\n1 0\nd -1 0\n0\n", num_vars=1)
    assert steps == [(2, False, (1,)), (3, True, (-1,)), (4, False, ())]


# ---------------------------------------------------------------- integration with the runner
def test_the_runner_can_certify_with_the_drat_checker():
    record = R.run_instance({"id": "chain", "family": "unit", "expected": "UNSAT"}, CHAIN, "cdcl", budget_s=5.0,
                            proof_checker="drat")
    assert record["status"] == "UNSAT"
    assert record["certification"] == "DRAT_RUP_CHECKED"
    assert record["disagreement"] is False


def test_the_runner_still_refuses_a_proof_the_drat_checker_rejects(monkeypatch):
    bogus = cdcl.Result(status="UNSAT", model=None, proof=[[1]], conflicts=1)

    def fake_solve(formula, *, deadline_s, seed=0):
        return bogus

    monkeypatch.setattr(R.cdcl, "solve", fake_solve)
    record = R.run_instance({"id": "chain", "family": "unit", "expected": "UNSAT"}, CHAIN, "cdcl", budget_s=5.0,
                            proof_checker="drat")
    assert record["status"] == "UNKNOWN"
    assert record["certification"] == "NONE"
    assert "independent checker" in record["note"]


def test_an_unknown_checker_name_is_refused_instead_of_silently_using_rup():
    with pytest.raises(R.UnknownProofChecker):
        R.run_instance({"id": "chain", "family": "unit"}, CHAIN, "cdcl", budget_s=5.0, proof_checker="drat2")
