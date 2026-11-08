"""NP benchmark, slice 1 (SAT): strict DIMACS, generators with known answers, independent verifiers, CDCL with a checked proof, WalkSAT, runner."""
import itertools
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import cnf as C  # noqa: E402
from npbench import gen_sat as G  # noqa: E402
from npbench import proof as P  # noqa: E402
from npbench import runner as R  # noqa: E402
from npbench.solvers import cdcl, walksat  # noqa: E402


# ---------------------------------------------------------------- strict DIMACS
GOOD = "c hello\np cnf 3 2\n1 -2 0\n2 3 0\n"


def test_parse_roundtrip():
    f = C.parse_dimacs(GOOD)
    assert f.num_vars == 3 and f.clauses == ((1, -2), (2, 3))
    assert C.parse_dimacs(C.write_dimacs(f)) == f


@pytest.mark.parametrize("text,why", [
    ("1 2 0\n", "no header"),
    ("p cnf 2 1\n1 2 0\np cnf 2 1\n", "duplicate header"),
    ("p cnf 2 2\n1 2 0\n", "declared clause count differs from the parsed count"),
    ("p cnf 2 1\n1 2 0\n-1 0\n", "more clauses than declared"),
    ("p cnf 2 1\n1 2\n", "unterminated last clause"),
    ("p cnf 2 1\n1 3 0\n", "literal above the variable count"),
    ("p CNF 2 1\n1 2 0\n", "uppercase CNF"),
    ("p cnf 2 1\n1_0 2 0\n", "underscore token"),
    ("p cnf 2 1\n+1 2 0\n", "plus sign"),
    ("p cnf 2 1\n1 ٣ 0\n", "non-ascii digit"),
    ("p cnf 2 1\n1 x 0\n", "non-integer"),
    ("p cnf -2 1\n1 0\n", "negative count"),
    ("p cnf 2 1 extra\n1 0\n", "extra header token"),
    ("p cnf 2 1\n1 2 0\n% \n5\n", "garbage after the percent terminator"),
])
def test_strict_parser_refuses(text, why):
    with pytest.raises(C.CnfError):
        C.parse_dimacs(text)


def test_percent_terminator_is_accepted_only_in_the_satlib_form():
    assert C.parse_dimacs("p cnf 2 1\n1 2 0\n%\n0\n\n").clauses == ((1, 2),)


def test_caps_are_enforced_before_allocation():
    with pytest.raises(C.CnfError):
        C.parse_dimacs(f"p cnf {C.MAX_VARS + 1} 1\n1 0\n")
    with pytest.raises(C.CnfError):
        C.parse_dimacs(f"p cnf 2 {C.MAX_CLAUSES + 1}\n1 0\n")
    with pytest.raises(C.CnfError):
        C.parse_dimacs("p cnf 2 1\n" + "1" * 40 + " 0\n")  # absurdly long digit string
    with pytest.raises(C.CnfError):
        C.parse_dimacs("c " + "x" * (C.MAX_BYTES + 1))


def test_duplicate_literals_and_tautologies_are_kept_as_written():
    f = C.parse_dimacs("p cnf 2 2\n1 1 0\n1 -1 0\n")
    assert f.clauses == ((1, 1), (1, -1))


def test_empty_clause_is_legal_and_unsat():
    f = C.parse_dimacs("p cnf 1 1\n0\n")
    assert f.clauses == ((),)
    assert not C.verify_model(f, {1: True})


def test_verify_model_needs_a_full_model():
    f = C.parse_dimacs("p cnf 2 1\n-1 -2 0\n")
    assert C.verify_model(f, {1: False, 2: False})
    assert not C.verify_model(f, {1: False}), "an unassigned variable must not count as false"
    assert not C.verify_model(f, {1: True, 2: True})
    assert not C.verify_model(f, {1: 1, 2: 0}), "values must be real booleans"


# ------------------------------------------------------------------- generators
def test_random_ksat_shape_and_determinism():
    f = G.random_ksat(30, 100, k=3, seed=7)
    assert f.num_vars == 30 and len(f.clauses) == 100
    for clause in f.clauses:
        assert len(clause) == 3 and len({abs(x) for x in clause}) == 3
    assert f == G.random_ksat(30, 100, k=3, seed=7)
    assert f != G.random_ksat(30, 100, k=3, seed=8)


def test_threshold_ratio_and_bad_arguments():
    f = G.threshold_instance(50, seed=1)
    assert len(f.clauses) == round(4.26 * 50)
    for bad in [dict(n=2, m=1, k=3), dict(n=10, m=-1, k=3), dict(n=10, m=5, k=1)]:
        with pytest.raises(ValueError):
            G.random_ksat(seed=0, **bad)


def test_planted_instance_is_satisfied_by_its_plant():
    f, plant = G.planted_ksat(40, 170, k=3, seed=3)
    assert C.verify_model(f, plant)


def test_factoring_known_answers():
    f, expected = G.factoring_cnf(15, bits_p=3, bits_q=3)
    assert expected == "SAT"
    res = cdcl.solve(f, deadline_s=20)
    assert res.status == "SAT" and C.verify_model(f, res.model)
    p, q = G.decode_factors(res.model, 3, 3)
    assert p * q == 15 and p > 1 and q > 1


@pytest.mark.parametrize("n", [13, 11, 7])
def test_factoring_a_prime_is_unsat_with_a_checked_proof(n):
    f, expected = G.factoring_cnf(n, bits_p=3, bits_q=3)
    assert expected == "UNSAT"
    res = cdcl.solve(f, deadline_s=30)
    assert res.status == "UNSAT"
    assert P.check_rup(f, res.proof), "the proof must be accepted by the independent checker"


def test_factoring_matches_brute_force_for_every_small_n():
    for n in range(2, 40):
        f, expected = G.factoring_cnf(n, bits_p=3, bits_q=3)
        truth = any(p * q == n for p in range(2, 8) for q in range(2, 8))
        assert expected == ("SAT" if truth else "UNSAT"), n
        res = cdcl.solve(f, deadline_s=30)
        assert res.status == expected, n
        if res.status == "SAT":
            assert C.verify_model(f, res.model)


def test_factoring_refuses_a_number_that_does_not_fit():
    with pytest.raises(ValueError):
        G.factoring_cnf(64, bits_p=3, bits_q=3)


# ---------------------------------------------------------------------- solvers
def brute_force(f):
    for bits in itertools.product([False, True], repeat=f.num_vars):
        model = {i + 1: b for i, b in enumerate(bits)}
        if C.verify_model(f, model):
            return "SAT"
    return "UNSAT"


def test_cdcl_agrees_with_brute_force_on_random_small_formulas_and_every_answer_is_backed():
    rng = random.Random(2026)
    sat = unsat = 0
    for i in range(160):
        n = rng.randint(3, 9)
        m = rng.randint(n, 6 * n)
        f = G.random_ksat(n, m, k=3, seed=rng.randint(0, 10**9))
        res = cdcl.solve(f, deadline_s=20)
        assert res.status == brute_force(f), (n, m, i)
        if res.status == "SAT":
            sat += 1
            assert C.verify_model(f, res.model)
        else:
            unsat += 1
            assert P.check_rup(f, res.proof)
    assert sat > 20 and unsat > 20, "the sample must exercise both verdicts"


def test_cdcl_handles_units_empty_clauses_duplicates_and_tautologies():
    assert cdcl.solve(C.parse_dimacs("p cnf 1 1\n0\n"), deadline_s=5).status == "UNSAT"
    assert cdcl.solve(C.parse_dimacs("p cnf 1 2\n1 0\n-1 0\n"), deadline_s=5).status == "UNSAT"
    r = cdcl.solve(C.parse_dimacs("p cnf 2 3\n1 1 0\n1 -1 0\n-2 -2 2 0\n"), deadline_s=5)
    assert r.status == "SAT" and C.verify_model(C.parse_dimacs("p cnf 2 3\n1 1 0\n1 -1 0\n-2 -2 2 0\n"), r.model)
    assert cdcl.solve(C.parse_dimacs("p cnf 3 0\n"), deadline_s=5).status == "SAT"


def test_cdcl_timeout_is_unknown_not_unsat():
    f = G.threshold_instance(150, seed=5)
    res = cdcl.solve(f, deadline_s=0.0)
    assert res.status == "UNKNOWN" and res.model is None and res.proof is None


def test_walksat_finds_models_but_never_claims_unsat():
    f, _ = G.planted_ksat(60, 200, k=3, seed=11)
    r = walksat.solve(f, deadline_s=10, seed=1)
    assert r.status == "SAT" and C.verify_model(f, r.model)
    unsat = C.parse_dimacs("p cnf 1 2\n1 0\n-1 0\n")
    assert walksat.solve(unsat, deadline_s=0.2, seed=1).status == "UNKNOWN"


# ------------------------------------------------------------- proof checker
def test_the_proof_checker_rejects_wrong_and_incomplete_proofs():
    f = C.parse_dimacs("p cnf 2 4\n1 2 0\n-1 2 0\n1 -2 0\n-1 -2 0\n")
    assert P.check_rup(f, [[2], [1], []]), "a correct hand-written RUP refutation must be accepted"
    assert not P.check_rup(f, [[1], [2], [-1]]), "a proof that never reaches the empty clause is refused"
    assert not P.check_rup(f, []), "an empty proof refutes nothing"
    assert not P.check_rup(f, [[1]]), "must end with the empty clause"
    sat_f = C.parse_dimacs("p cnf 2 1\n1 2 0\n")
    assert not P.check_rup(sat_f, [[]]), "the empty clause is not RUP for a satisfiable formula"
    assert not P.check_rup(sat_f, [[-1], []]), "a lemma that does not follow must be refused"


# ----------------------------------------------------------------------- runner
def test_runner_reports_only_backed_verdicts():
    f, expected = G.factoring_cnf(15, bits_p=3, bits_q=3)
    rec = R.run_instance({"id": "fac15", "family": "factoring", "expected": expected}, f, "cdcl", budget_s=20)
    assert rec["status"] == "SAT" and rec["certification"] == "MODEL_VERIFIED" and rec["disagreement"] is False
    g, e2 = G.factoring_cnf(13, bits_p=3, bits_q=3)
    rec2 = R.run_instance({"id": "fac13", "family": "factoring", "expected": e2}, g, "cdcl", budget_s=20)
    assert rec2["status"] == "UNSAT" and rec2["certification"] == "RUP_CHECKED" and rec2["disagreement"] is False


def test_runner_turns_a_bad_model_or_bad_proof_into_unknown(monkeypatch):
    f = C.parse_dimacs("p cnf 2 1\n1 2 0\n")
    bad_model = cdcl.Result("SAT", {1: False, 2: False}, None, 0)
    monkeypatch.setitem(R.SOLVERS, "liar_sat", lambda formula, budget_s, seed: bad_model)
    rec = R.run_instance({"id": "x", "family": "t", "expected": "SAT"}, f, "liar_sat", budget_s=1)
    assert rec["status"] == "UNKNOWN" and rec["certification"] == "NONE" and "refused" in rec["note"]
    unsat_f = C.parse_dimacs("p cnf 1 1\n1 0\n")
    bad_proof = cdcl.Result("UNSAT", None, [[]], 0)
    monkeypatch.setitem(R.SOLVERS, "liar_unsat", lambda formula, budget_s, seed: bad_proof)
    rec2 = R.run_instance({"id": "y", "family": "t", "expected": "SAT"}, unsat_f, "liar_unsat", budget_s=1)
    assert rec2["status"] == "UNKNOWN" and "refused" in rec2["note"]


def test_runner_flags_a_disagreement_with_the_known_answer(monkeypatch):
    f = C.parse_dimacs("p cnf 1 1\n1 0\n")
    rec = R.run_instance({"id": "z", "family": "t", "expected": "UNSAT"}, f, "cdcl", budget_s=5)
    assert rec["status"] == "SAT" and rec["disagreement"] is True


def test_runner_reports_an_unknown_solver_as_unavailable_not_as_a_fallback():
    f = C.parse_dimacs("p cnf 1 1\n1 0\n")
    rec = R.run_instance({"id": "u", "family": "t", "expected": None}, f, "kissat", budget_s=1)
    assert rec["status"] == "unavailable" and "kissat" in rec["note"]


def test_par2_score_counts_unknowns_as_twice_the_budget():
    recs = [{"status": "SAT", "elapsed_s": 1.0, "budget_s": 10}, {"status": "UNKNOWN", "elapsed_s": 10.0, "budget_s": 10},
            {"status": "UNSAT", "elapsed_s": 3.0, "budget_s": 10}]
    assert R.par2(recs) == pytest.approx((1.0 + 20.0 + 3.0) / 3)
    assert R.par2([]) is None


def test_manifest_entry_binds_the_instance_to_its_bytes():
    f = G.random_ksat(20, 60, seed=1)
    entry = R.manifest_entry("rand20", "random3sat", {"n": 20, "m": 60, "seed": 1}, f, expected=None)
    import hashlib
    assert entry["sha256"] == hashlib.sha256(C.write_dimacs(f).encode("ascii")).hexdigest()
    assert entry["generator"] == G.GENERATOR_VERSION and entry["params"] == {"n": 20, "m": 60, "seed": 1}
