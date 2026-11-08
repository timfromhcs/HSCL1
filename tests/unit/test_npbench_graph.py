"""NP benchmark, slice 3 (graphs): colouring, clique, Hamiltonian cycle with known-answer generators and independent verifiers."""
import itertools
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import __main__ as cli  # noqa: E402
from npbench import gen_graph as GG  # noqa: E402
from npbench import graph as G  # noqa: E402
from npbench import graph_runner as GR  # noqa: E402
from npbench import graph_solvers as GS  # noqa: E402
from npbench import proof as P  # noqa: E402
from npbench import suites as S  # noqa: E402
from npbench.solvers import cdcl  # noqa: E402


# ------------------------------------------------------------------ strict .col
def test_col_roundtrip_and_strict_refusals():
    g = GG.cycle(5)
    assert G.parse_col(G.write_col(g)) == g
    bad = [
        "e 1 2\n", "p edge 3 1\ne 1 1\n", "p edge 3 1\ne 1 4\n", "p edge 3 2\ne 1 2\n", "p edge 3 1\ne 1 2\ne 2 1\n", "p edge 3 2\ne 1 2\ne 2 1\n",
        "p edge 3 1\np edge 3 1\ne 1 2\n", "p col 3 1\ne 1 2\n", "p edge 3 1\ne 1_0 2\n", "p edge 3 1\ne +1 2\n",
        "p edge 3 1\nx 1 2\n", f"p edge {G.MAX_VERTICES + 1} 0\n", "p edge 3 1\ne 1 2 3\n",
    ]
    for text in bad:
        with pytest.raises(G.GraphError):
            G.parse_col(text)


def test_verifiers_reject_wrong_witnesses():
    tri = GG.complete(3)
    assert G.verify_coloring(tri, {1: 0, 2: 1, 3: 2}, 3)
    assert not G.verify_coloring(tri, {1: 0, 2: 1, 3: 1}, 3), "adjacent vertices share a colour"
    assert not G.verify_coloring(tri, {1: 0, 2: 1, 3: 3}, 3), "colour out of range"
    assert not G.verify_coloring(tri, {1: 0, 2: 1}, 3), "a vertex is missing"
    assert not G.verify_coloring(tri, {1: 0, 2: 1, 3: True}, 3), "booleans are not colours"
    assert G.verify_clique(tri, [1, 2, 3], 3) and not G.verify_clique(tri, [1, 2, 2], 3)
    path = G.Graph(4, ((1, 2), (2, 3), (3, 4)))
    assert not G.verify_clique(path, [1, 2, 3], 3)
    sq = GG.cycle(4)
    assert G.verify_ham_cycle(sq, [1, 2, 3, 4]) and G.verify_ham_cycle(sq, [3, 2, 1, 4])
    assert not G.verify_ham_cycle(sq, [1, 3, 2, 4]) and not G.verify_ham_cycle(sq, [1, 2, 3]) and not G.verify_ham_cycle(sq, [1, 2, 3, 3])
    assert not G.verify_ham_cycle(path, [1, 2, 3, 4]), "a Hamiltonian path is not a cycle: the closing edge 4-1 is missing"


# ----------------------------------------------------------------- generators
@pytest.mark.parametrize("k,vertices", [(2, 2), (3, 5), (4, 11), (5, 23)])
def test_mycielski_sizes_and_triangle_freeness(k, vertices):
    g = GG.mycielski(k)
    assert g.n == vertices
    adj = g.adjacency()
    assert not any(adj[u] & adj[v] for u, v in g.edges), "Mycielski graphs are triangle-free"


def brute_chromatic(g):
    for k in range(1, g.n + 1):
        for colors in itertools.product(range(k), repeat=g.n):
            if all(colors[u - 1] != colors[v - 1] for u, v in g.edges):
                return k
    raise AssertionError


@pytest.mark.parametrize("k", [2, 3])
def test_mycielski_chromatic_number_matches_brute_force(k):
    # M4 (11 vertices) is too large for brute force; its value is certified by the SAT/UNSAT pair in the runner tests
    assert brute_chromatic(GG.mycielski(k)) == k


def test_turan_queen_and_petersen_shapes():
    t = GG.turan(10, 3)
    assert t.n == 10 and len(t.edges) == 45 - (6 + 3 + 3)  # parts of size 4, 3, 3 are independent sets
    q = GG.queen(5)
    assert q.n == 25 and len(q.edges) == 160  # 5x5 queen graph: 10 rook lines of C(5,2) each plus the diagonals
    assert (1, 2) in q.edges and (1, 7) in q.edges and (1, 8) not in q.edges  # same row, same diagonal, knight move
    with pytest.raises(ValueError):
        GG.generalized_petersen(4, 2)


def test_known_values_table():
    assert GG.known(("mycielski", {"k": 4})) == {"chi": 4, "omega": 2}
    assert GG.known(("queen", {"n": 5})) == {"chi": 5, "omega": 5}
    assert GG.known(("queen", {"n": 6})) == {}, "queens with n sharing a factor with 6 are not claimed"
    assert GG.known(("turan", {"n": 12, "r": 4})) == {"chi": 4, "omega": 4}


def exhaustive_ham(g):
    adj = g.adjacency()

    def extend(path, seen):
        if len(path) == g.n:
            return path[0] in adj[path[-1]]
        return any(extend(path + [v], seen | {v}) for v in adj[path[-1]] if v not in seen)

    return extend([1], {1})


def test_petersen_family_theorem_matches_exhaustive_search_on_small_cases():
    checked = 0
    for n in range(5, 13):
        for k in range(1, (n + 1) // 2):
            if 2 * k >= n:
                continue
            g = GG.generalized_petersen(n, k)
            assert GG.petersen_is_hamiltonian(n, k) == exhaustive_ham(g), (n, k)
            checked += 1
    assert checked >= 12


def test_planted_generators_hold_their_promise():
    g, colors = GG.planted_kcolorable(30, 90, 4, seed=1)
    assert G.verify_coloring(g, colors, 4)
    h, clique = GG.planted_clique(40, 0.3, 8, seed=2)
    assert G.verify_clique(h, clique, 8)
    p, cycle = GG.planted_ham(25, 12, seed=3)
    assert G.verify_ham_cycle(p, cycle)
    assert GG.planted_ham(25, 12, seed=3)[0] == p, "deterministic for a seed"


# ------------------------------------------------------------------ encodings
def test_coloring_encoding_agrees_with_brute_force_on_random_small_graphs():
    import random
    rng = random.Random(5)
    seen = set()
    for _ in range(40):
        n = rng.randint(3, 6)
        edges = tuple(sorted({tuple(sorted(rng.sample(range(1, n + 1), 2))) for _ in range(rng.randint(1, 10))}))
        g = G.Graph(n, edges)
        chi = brute_chromatic(g)
        for k in (chi - 1, chi):
            if k < 1:
                continue
            res = cdcl.solve(GS.coloring_cnf(g, k), deadline_s=10)
            assert res.status == ("SAT" if k >= chi else "UNSAT"), (g, k)
            seen.add(res.status)
            if res.status == "UNSAT":
                assert P.check_rup(GS.coloring_cnf(g, k), res.proof)
            else:
                assert G.verify_coloring(g, GS.decode_coloring(res.model, g, k), k)
    assert seen == {"SAT", "UNSAT"}


def test_ham_encoding_agrees_with_exhaustive_search():
    import random
    rng = random.Random(9)
    seen = set()
    for _ in range(30):
        n = rng.randint(3, 7)
        edges = tuple(sorted({tuple(sorted(rng.sample(range(1, n + 1), 2))) for _ in range(rng.randint(n - 1, 3 * n))}))
        g = G.Graph(n, edges)
        res = cdcl.solve(GS.ham_cnf(g), deadline_s=10)
        assert res.status == ("SAT" if exhaustive_ham(g) else "UNSAT"), g
        seen.add(res.status)
        if res.status == "SAT":
            assert G.verify_ham_cycle(g, GS.decode_ham(res.model, g))
        else:
            assert P.check_rup(GS.ham_cnf(g), res.proof)
    assert seen == {"SAT", "UNSAT"}


# -------------------------------------------------------------------- solvers
def test_dsatur_colours_validly_and_is_optimal_on_complete_multipartite():
    t = GG.turan(12, 4)
    res = GS.dsatur(t, 4, deadline_s=5)
    assert res.status == "SAT" and G.verify_coloring(t, res.witness, 4)
    assert GS.dsatur(GG.complete(5), 4, deadline_s=5).status == "UNKNOWN", "a heuristic never claims UNSAT"


def test_clique_search_finds_the_maximum_and_never_claims_more():
    t = GG.turan(12, 4)
    res = GS.max_clique(t, deadline_s=5)
    assert len(res.witness) == 4 and G.verify_clique(t, res.witness, 4) and res.complete
    h, plant = GG.planted_clique(40, 0.3, 8, seed=2)
    found = GS.max_clique(h, deadline_s=10)
    assert len(found.witness) >= 8 and G.verify_clique(h, found.witness, len(found.witness))


def test_ham_backtrack_finds_witness_only():
    p, _ = GG.planted_ham(20, 10, seed=4)
    assert GS.ham_backtrack(p, deadline_s=10).status == "SAT"
    assert GS.ham_backtrack(GG.generalized_petersen(5, 2), deadline_s=2).status == "UNKNOWN", "no certificate, no UNSAT"


# --------------------------------------------------------------------- runner
def task_spec(ident, graph, params, task, expected):
    return {"id": ident, "family": "graph", "params": {"graph": graph, **params}, "task": task, "expected": expected}


def test_coloring_pair_is_certified_both_ways():
    g = GG.mycielski(4)
    sat = GR.run_graph_instance(task_spec("m4k4", "mycielski", {"k": 4}, {"kind": "coloring", "k": 4}, "SAT"), g, "sat", budget_s=30)
    assert sat["status"] == "SAT" and sat["certification"] == "WITNESS_VERIFIED" and not sat["disagreement"]
    unsat = GR.run_graph_instance(task_spec("m4k3", "mycielski", {"k": 4}, {"kind": "coloring", "k": 3}, "UNSAT"), g, "sat", budget_s=60)
    assert unsat["status"] == "UNSAT" and unsat["certification"] == "RUP_CHECKED" and not unsat["disagreement"]


def test_clique_no_answer_is_certified_by_a_colouring_bound():
    t = GG.turan(12, 4)
    yes = GR.run_graph_instance(task_spec("t12c4", "turan", {"n": 12, "r": 4}, {"kind": "clique", "k": 4}, "SAT"), t, "bk", budget_s=10)
    assert yes["status"] == "SAT" and yes["certification"] == "WITNESS_VERIFIED"
    no = GR.run_graph_instance(task_spec("t12c5", "turan", {"n": 12, "r": 4}, {"kind": "clique", "k": 5}, "UNSAT"), t, "bk", budget_s=10)
    assert no["status"] == "UNSAT" and no["certification"] == "COLORING_BOUND_VERIFIED" and not no["disagreement"]


def test_exhaustive_clique_search_without_a_certificate_is_unknown(monkeypatch):
    t = GG.turan(12, 4)
    monkeypatch.setattr(GS, "dsatur", lambda g, k, deadline_s: GS.GraphResult("UNKNOWN", None, None, None, 0, "disabled"))
    monkeypatch.setattr(GS, "sat_coloring", lambda g, k, deadline_s: GS.GraphResult("UNKNOWN", None, None, None, 0, "disabled"))
    rec = GR.run_graph_instance(task_spec("t12c5b", "turan", {"n": 12, "r": 4}, {"kind": "clique", "k": 5}, "UNSAT"), t, "bk", budget_s=5)
    assert rec["status"] == "UNKNOWN" and "certificate" in rec["note"]


def test_runner_refuses_a_wrong_witness_and_an_unproved_no(monkeypatch):
    g = GG.complete(4)
    monkeypatch.setitem(GR.GRAPH_SOLVERS["coloring"], "liar", lambda graph, k, deadline_s: GS.GraphResult("SAT", {1: 0, 2: 0, 3: 0, 4: 0}, None, None, 0, ""))
    rec = GR.run_graph_instance(task_spec("liar", "complete", {"n": 4}, {"kind": "coloring", "k": 4}, "SAT"), g, "liar", budget_s=1)
    assert rec["status"] == "UNKNOWN" and "refused" in rec["note"]
    monkeypatch.setitem(GR.GRAPH_SOLVERS["coloring"], "liar2", lambda graph, k, deadline_s: GS.GraphResult("UNSAT", None, "RUP", [[]], 0, ""))
    rec2 = GR.run_graph_instance(task_spec("liar2", "complete", {"n": 4}, {"kind": "coloring", "k": 4}, "SAT"), g, "liar2", budget_s=1)
    assert rec2["status"] == "UNKNOWN" and "refused" in rec2["note"]


def test_clique_no_answer_with_a_bad_colouring_bound_is_refused(monkeypatch):
    t = GG.turan(12, 4)
    invalid = {v: 0 for v in range(1, 13)}  # adjacent vertices share colour 0
    too_many = {v: (v - 1) % 5 for v in range(1, 13)}  # five colours are in use, but k - 1 = 4 are allowed
    for name, cert in (("bad1", invalid), ("bad2", too_many)):
        monkeypatch.setitem(GR.GRAPH_SOLVERS["clique"], name, lambda g, k, deadline_s, cert=cert: GS.GraphResult("UNSAT", None, "COLORING_BOUND", cert, 0, ""))
        rec = GR.run_graph_instance(task_spec(name, "turan", {"n": 12, "r": 4}, {"kind": "clique", "k": 5}, "UNSAT"), t, name, budget_s=1)
        assert rec["status"] == "UNKNOWN" and "refused" in rec["note"], name


def test_runner_flags_a_known_answer_disagreement():
    g = GG.complete(4)
    rec = GR.run_graph_instance(task_spec("dis", "complete", {"n": 4}, {"kind": "coloring", "k": 4}, "UNSAT"), g, "sat", budget_s=10)
    assert rec["status"] == "SAT" and rec["disagreement"] is True


# ---------------------------------------------------------------- suite + CLI
def test_graph_suite_claims_match_the_generators_and_ids_are_unique():
    specs = S.suite_specs("graphs")
    assert len({s["id"] for s in specs}) == len(specs) >= 12
    for spec in specs:
        graph, truth = S.build_graph_instance(spec)
        assert truth == spec["expected"], spec["id"]
    assert {"SAT", "UNSAT"} <= {s["expected"] for s in specs}
    kinds = {s["task"]["kind"] for s in specs}
    assert kinds == {"coloring", "clique", "hamcycle"}


def test_a_claim_the_graph_generator_does_not_know_is_refused():
    spec = task_spec("bad", "queen", {"n": 6}, {"kind": "coloring", "k": 6}, "UNSAT")
    with pytest.raises(ValueError):
        S.build_graph_instance(spec)


def test_graphs_suite_through_the_cli_decides_everything_with_checked_evidence(tmp_path):
    out = tmp_path / "graphs.json"
    code = cli.main(["run", "--suite", "graphs", "--solvers", "sat,dsatur,bk,backtrack", "--budget", "60", "--out", str(out)])
    rep = json.loads(out.read_text())
    assert code == 0, rep["summary"]
    for name, summary in rep["summary"].items():
        assert summary["disagreements"] == 0 and summary["refused"] == 0 and summary["unavailable"] == 0, name
    decided_by_sat = [r for r in rep["records"] if r["solver"] == "sat" and r["status"] in ("SAT", "UNSAT")]
    assert decided_by_sat, "the SAT route must decide something"
    for rec in rep["records"]:
        if rec["status"] == "UNSAT":
            assert rec["certification"] in ("RUP_CHECKED", "COLORING_BOUND_VERIFIED")
        if rec["status"] == "SAT":
            assert rec["certification"] == "WITNESS_VERIFIED"
    sat_ids = {r["id"] for r in rep["records"] if r["solver"] == "sat" and r["status"] in ("SAT", "UNSAT")}
    assert len(sat_ids) >= 8
