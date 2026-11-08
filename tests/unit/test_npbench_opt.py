"""NP benchmark, slice 4 (optimisation): TSP and knapsack / subset sum with exact ground truth and checkable certificates."""
import itertools
import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import __main__ as cli  # noqa: E402
from npbench import gen_knap as GK  # noqa: E402
from npbench import gen_tsp as GT  # noqa: E402
from npbench import knap as K  # noqa: E402
from npbench import knap_solvers as KS  # noqa: E402
from npbench import opt_runner as OR  # noqa: E402
from npbench import suites as S  # noqa: E402
from npbench import tsp as T  # noqa: E402
from npbench import tsp_solvers as TS  # noqa: E402


# ------------------------------------------------------------------------ TSP
def test_euc2d_rounding_matches_the_float_definition_and_is_exact():
    rng = random.Random(1)
    for _ in range(2000):
        a, b = (rng.randint(-500, 500), rng.randint(-500, 500)), (rng.randint(-500, 500), rng.randint(-500, 500))
        d2 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        assert T.euc2d(a, b) == int(math.sqrt(d2) + 0.5)
    assert T.euc2d((0, 0), (3, 4)) == 5 and T.euc2d((0, 0), (1, 1)) == 1 and T.euc2d((0, 0), (2, 2)) == 3
    assert T.euc2d((0, 0), (10**9, 10**9)) == round(math.sqrt(2) * 10**9)


def tiny(n, seed):
    return GT.random_euclid(n, seed=seed, box=100)


def brute_opt(inst):
    d = inst.matrix()
    best = None
    for perm in itertools.permutations(range(1, inst.n)):
        order = (0,) + perm
        length = sum(d[order[i]][order[(i + 1) % inst.n]] for i in range(inst.n))
        best = length if best is None else min(best, length)
    return best


def test_verify_tour_demands_a_permutation_and_computes_length_independently():
    inst = tiny(6, 1)
    d = inst.matrix()
    order = [3, 1, 4, 0, 5, 2]
    assert T.verify_tour(inst, order) == sum(d[order[i]][order[(i + 1) % 6]] for i in range(6))
    for bad in ([0, 1, 2, 3, 4], [0, 1, 2, 3, 4, 4], [0, 1, 2, 3, 4, 6], [0, 1, 2, 3, 4, True], "012345"):
        assert T.verify_tour(inst, bad) is None


def test_held_karp_dp_matches_brute_force_and_returns_a_valid_optimal_tour():
    for seed in range(12):
        inst = tiny(7, seed)
        length, tour = TS.held_karp(inst)
        assert length == brute_opt(inst), seed
        assert T.verify_tour(inst, tour) == length


def test_nearest_neighbour_two_opt_gives_valid_tours_never_below_the_optimum():
    ratios = []
    for seed in range(20):
        inst = tiny(10, seed)
        opt, _ = TS.held_karp(inst)
        res = TS.nn_two_opt(inst, deadline_s=5)
        length = T.verify_tour(inst, res.witness)
        assert length is not None and length >= opt
        ratios.append(length / opt)
    assert max(ratios) < 1.35 and sum(ratios) / len(ratios) < 1.12, ratios


def test_lagrangian_bound_is_valid_for_any_potentials():
    for seed in range(15):
        inst = tiny(8, seed)
        opt, _ = TS.held_karp(inst)
        rng = random.Random(seed)
        assert T.lower_bound(inst, [0] * 8) <= opt
        for _ in range(10):
            pi = [rng.randint(-60, 60) for _ in range(8)]
            assert T.lower_bound(inst, pi) <= opt, (seed, pi)


def test_subgradient_bound_improves_on_the_plain_one_tree_and_stays_valid():
    gains = 0
    for seed in range(15):
        inst = tiny(10, seed)
        opt, _ = TS.held_karp(inst)
        pi = TS.optimise_potentials(inst, upper=opt, deadline_s=5)
        lb = T.lower_bound(inst, pi)
        assert T.lower_bound(inst, [0] * 10) <= lb <= opt
        gains += lb > T.lower_bound(inst, [0] * 10)
        assert lb >= 0.9 * opt, (seed, lb, opt)
    assert gains >= 5, "the optimiser must improve on the plain 1-tree for a good share of the instances"


def test_bad_potentials_are_rejected_by_the_verifier():
    inst = tiny(6, 3)
    for bad in ([0] * 5, [0] * 7, [0, 0, 0, 0, 0, True], [0, 0, 0, 0, 0, 1.5], None):
        assert T.lower_bound(inst, bad) is None


def test_strict_tsplib_reader():
    text = "NAME : t\nTYPE : TSP\nDIMENSION : 3\nEDGE_WEIGHT_TYPE : EUC_2D\nNODE_COORD_SECTION\n1 0 0\n2 3 4\n3 6 0\nEOF\n"
    inst = T.parse_tsplib(text)
    assert inst.n == 3 and inst.matrix()[0][1] == 5
    for bad in [text.replace("EUC_2D", "GEO"), text.replace("DIMENSION : 3", "DIMENSION : 4"), text.replace("2 3 4", "2 3.5 4"),
                text.replace("1 0 0", "2 0 0"), text.replace("TYPE : TSP", "TYPE : ATSP"), text.replace("NODE_COORD_SECTION\n", ""),
                "x" * (T.MAX_BYTES + 1)]:
        with pytest.raises(T.TspError):
            T.parse_tsplib(bad)


# ------------------------------------------------------------------- knapsack
def test_families_follow_their_definitions():
    for seed in range(3):
        sub = GK.generate("subset_sum", 20, 1000, seed=seed)
        assert all(w == p for w, p in sub.items)
        strong = GK.generate("strongly_correlated", 20, 1000, seed=seed)
        assert all(p == w + 100 for w, p in strong.items)
        unc = GK.generate("uncorrelated", 20, 1000, seed=seed)
        assert all(1 <= w <= 1000 and 1 <= p <= 1000 for w, p in unc.items)
        weak = GK.generate("weakly_correlated", 20, 1000, seed=seed)
        assert all(1 <= p and abs(p - w) <= 100 for w, p in weak.items)
        for inst in (sub, strong, unc, weak):
            assert all(1 <= w <= 1000 for w, _ in inst.items) and 0 < inst.capacity < sum(w for w, _ in inst.items)
    assert GK.generate("strongly_correlated", 20, 1000, seed=1) == GK.generate("strongly_correlated", 20, 1000, seed=1)
    with pytest.raises(ValueError):
        GK.generate("nope", 5, 10, seed=0)


def brute_knap(inst):
    best = 0
    for mask in range(1 << len(inst.items)):
        w = sum(inst.items[i][0] for i in range(len(inst.items)) if mask >> i & 1)
        if w <= inst.capacity:
            best = max(best, sum(inst.items[i][1] for i in range(len(inst.items)) if mask >> i & 1))
    return best


@pytest.mark.parametrize("family", ["uncorrelated", "weakly_correlated", "strongly_correlated", "subset_sum"])
def test_knapsack_dp_matches_brute_force_with_a_valid_witness(family):
    for seed in range(8):
        inst = GK.generate(family, 11, 40, seed=seed)
        value, chosen = KS.dp_optimum(inst)
        assert value == brute_knap(inst), (family, seed)
        assert K.verify_selection(inst, chosen, value)


def test_selection_verifier_rejects_wrong_selections():
    inst = K.Knapsack(((5, 10), (4, 7), (3, 4)), 8)
    assert K.verify_selection(inst, [0, 2], 14) and K.verify_selection(inst, [], 0)
    assert not K.verify_selection(inst, [0, 1], 17), "weight 9 exceeds the capacity 8"
    assert not K.verify_selection(inst, [0, 2], 15), "profit 14 is below the target 15"
    assert not K.verify_selection(inst, [2, 2], 8), "an item may be used once (weight 6 fits and profit 8 reaches the target)"
    assert not K.verify_selection(inst, [3], 0) and not K.verify_selection(inst, [-1], 0) and not K.verify_selection(inst, [True], 0)


def test_fractional_bound_dominates_the_optimum_and_is_exact_arithmetic():
    for family in ("uncorrelated", "strongly_correlated", "subset_sum"):
        for seed in range(8):
            inst = GK.generate(family, 12, 50, seed=seed)
            ub = K.fractional_upper_bound(inst)
            assert isinstance(ub, Fraction) and ub >= KS.dp_optimum(inst)[0]


def test_fractional_bound_known_value():
    # items by density: (3,4) 1.33, (5,10) 2.0, (4,7) 1.75 -> order (5,10), (4,7), (3,4); capacity 8 takes 5 + 3/4 of the 4-weight item
    assert K.fractional_upper_bound(K.Knapsack(((5, 10), (4, 7), (3, 4)), 8)) == Fraction(10) + Fraction(3, 4) * 7


def test_greedy_returns_a_valid_selection():
    inst = GK.generate("uncorrelated", 30, 100, seed=2)
    res = KS.greedy(inst, target=0)
    assert K.verify_selection(inst, res.witness, 0)


# ---------------------------------------------------------------------- runner
def tsp_spec(ident, bound, expected):
    return {"id": ident, "family": "tsp", "task": {"kind": "tsp", "bound": bound}, "expected": expected}


def test_tsp_yes_is_a_verified_tour_and_a_far_bound_no_is_certified():
    inst = tiny(10, 4)
    opt, _ = TS.held_karp(inst)
    yes = OR.run_opt_instance(tsp_spec("y", opt, "SAT"), inst, "dp", budget_s=20)
    assert yes["status"] == "SAT" and yes["certification"] == "WITNESS_VERIFIED" and not yes["disagreement"]
    heur = OR.run_opt_instance(tsp_spec("h", int(opt * 1.4), "SAT"), inst, "nn2opt", budget_s=20)
    assert heur["status"] == "SAT"
    low = math.floor(opt * 0.9)
    no = OR.run_opt_instance(tsp_spec("n", low, "UNSAT"), inst, "lagrange", budget_s=20)
    assert no["status"] == "UNSAT" and no["certification"] == "LOWER_BOUND_VERIFIED" and not no["disagreement"]


def test_tsp_exhaustive_dp_no_without_a_certificate_is_unknown():
    inst = tiny(10, 4)
    opt, _ = TS.held_karp(inst)
    rec = OR.run_opt_instance(tsp_spec("dpno", opt - 1, "UNSAT"), inst, "dp", budget_s=20)
    assert rec["status"] == "UNKNOWN" and rec["certification"] == "NONE" and "certificate" in rec["note"]


def test_tsp_runner_refuses_a_wrong_tour_and_a_weak_bound(monkeypatch):
    inst = tiny(8, 2)
    opt, _ = TS.held_karp(inst)
    monkeypatch.setitem(OR.OPT_SOLVERS["tsp"], "liar", lambda i, spec, deadline_s: TS.OptResult("SAT", [0, 1, 2, 3, 4, 5, 6, 6], None, None, 0, ""))
    rec = OR.run_opt_instance(tsp_spec("l", opt, "SAT"), inst, "liar", budget_s=1)
    assert rec["status"] == "UNKNOWN" and "refused" in rec["note"]
    monkeypatch.setitem(OR.OPT_SOLVERS["tsp"], "weak", lambda i, spec, deadline_s: TS.OptResult("UNSAT", None, "LOWER_BOUND", [0] * 8, 0, ""))
    rec2 = OR.run_opt_instance(tsp_spec("w", opt, "UNSAT"), inst, "weak", budget_s=1)
    assert rec2["status"] == "UNKNOWN" and "refused" in rec2["note"], "a bound that does not exceed the limit proves nothing"
    monkeypatch.setitem(OR.OPT_SOLVERS["tsp"], "short", lambda i, spec, deadline_s: TS.OptResult("SAT", list(range(8)), None, None, 0, ""))
    too_short = T.verify_tour(inst, list(range(8)))
    rec3 = OR.run_opt_instance(tsp_spec("s", too_short - 1, "UNSAT"), inst, "short", budget_s=1)
    assert rec3["status"] == "UNKNOWN" and "refused" in rec3["note"], "a tour longer than the bound is not a yes"


def knap_spec(ident, target, expected):
    return {"id": ident, "family": "knapsack", "task": {"kind": "knapsack", "target": target}, "expected": expected}


def test_knapsack_yes_no_and_the_honest_gap_on_strongly_correlated_instances():
    inst = GK.generate("uncorrelated", 25, 200, seed=3)
    opt, _ = KS.dp_optimum(inst)
    yes = OR.run_opt_instance(knap_spec("y", opt, "SAT"), inst, "dp", budget_s=20)
    assert yes["status"] == "SAT" and yes["certification"] == "WITNESS_VERIFIED"
    far = math.floor(K.fractional_upper_bound(inst)) + 1
    no = OR.run_opt_instance(knap_spec("n", far, "UNSAT"), inst, "ub", budget_s=20)
    assert no["status"] == "UNSAT" and no["certification"] == "LP_BOUND_VERIFIED" and not no["disagreement"]
    # between the optimum and the LP bound there may be a gap no certificate closes: the answer must stay UNKNOWN
    strong = GK.generate("strongly_correlated", 25, 200, seed=5)
    sopt, _ = KS.dp_optimum(strong)
    assert math.floor(K.fractional_upper_bound(strong)) > sopt, "this instance must have an LP gap for the test to mean anything"
    gap = OR.run_opt_instance(knap_spec("g", sopt + 1, "UNSAT"), strong, "ub", budget_s=20)
    assert gap["status"] == "UNKNOWN" and gap["certification"] == "NONE"
    dp_no = OR.run_opt_instance(knap_spec("g2", sopt + 1, "UNSAT"), strong, "dp", budget_s=20)
    assert dp_no["status"] == "UNKNOWN" and "certificate" in dp_no["note"]


def test_knapsack_runner_refuses_wrong_witnesses_and_flags_disagreements(monkeypatch):
    inst = K.Knapsack(((5, 10), (4, 7), (3, 4)), 8)
    monkeypatch.setitem(OR.OPT_SOLVERS["knapsack"], "liar", lambda i, spec, deadline_s: KS.OptResult("SAT", [0, 1], None, None, 0, ""))
    rec = OR.run_opt_instance(knap_spec("l", 17, "UNSAT"), inst, "liar", budget_s=1)
    assert rec["status"] == "UNKNOWN" and "refused" in rec["note"]
    monkeypatch.setitem(OR.OPT_SOLVERS["knapsack"], "bound_liar", lambda i, spec, deadline_s: KS.OptResult("UNSAT", None, "LP_BOUND", None, 0, ""))
    rec2 = OR.run_opt_instance(knap_spec("b", 14, "SAT"), inst, "bound_liar", budget_s=1)
    assert rec2["status"] == "UNKNOWN" and "refused" in rec2["note"], "14 is below the LP bound 15.25: not a certified no"
    wrong = OR.run_opt_instance(knap_spec("d", 14, "UNSAT"), inst, "dp", budget_s=5)
    assert wrong["status"] == "SAT" and wrong["disagreement"] is True


def test_unknown_solver_is_unavailable_and_a_solver_of_another_family_is_skipped():
    inst = K.Knapsack(((5, 10),), 8)
    assert OR.run_opt_instance(knap_spec("u", 10, None), inst, "kissat", budget_s=1)["status"] == "unavailable"
    assert OR.run_opt_instance(knap_spec("s", 10, None), inst, "nn2opt", budget_s=1) is None


# ------------------------------------------------------------------- suite / CLI
def test_optimization_suite_claims_match_exact_ground_truth_and_cover_both_families():
    specs = S.suite_specs("optimization")
    assert len({s["id"] for s in specs}) == len(specs) >= 12
    assert {s["family"] for s in specs} == {"tsp", "knapsack"}
    assert {"SAT", "UNSAT"} <= {s["expected"] for s in specs}
    for spec in specs:
        instance, truth = S.build_opt_instance(spec)
        assert truth == spec["expected"], spec["id"]


def test_a_wrong_optimisation_claim_is_refused():
    spec = dict(S.suite_specs("optimization")[0])
    spec["expected"] = {"SAT": "UNSAT", "UNSAT": "SAT"}[spec["expected"]]
    with pytest.raises(ValueError):
        S.build_opt_instance(spec)


def test_optimization_suite_through_the_cli(tmp_path):
    out = tmp_path / "opt.json"
    code = cli.main(["run", "--suite", "optimization", "--solvers", "dp,nn2opt,lagrange,greedy,ub", "--budget", "30", "--out", str(out)])
    rep = json.loads(out.read_text())
    assert code == 0, rep["summary"]
    for name, summary in rep["summary"].items():
        assert summary["disagreements"] == 0 and summary["refused"] == 0 and summary["unavailable"] == 0, name
    for rec in rep["records"]:
        if rec["status"] == "UNSAT":
            assert rec["certification"] in ("LOWER_BOUND_VERIFIED", "LP_BOUND_VERIFIED")
        if rec["status"] == "SAT":
            assert rec["certification"] == "WITNESS_VERIFIED"
    decided = {r["id"] for r in rep["records"] if r["status"] in ("SAT", "UNSAT")}
    assert len(decided) >= 10
    assert any(r["status"] == "UNKNOWN" and r["expected"] == "UNSAT" for r in rep["records"]), "the suite must contain an honest gap"
