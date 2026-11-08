"""Benchmark suites: a suite is a list of instance specs; an instance is rebuilt from its spec, never stored.

A spec is ``{"id", "family", "params", "expected"}``. ``expected`` is a claim about the answer. The generator is the
authority: if it knows the answer (planted, factoring) a different claim is refused, and if it does not (random,
threshold) a claim is refused too, so a suite file can never smuggle in an unverified "known answer".
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from fractions import Fraction
from functools import lru_cache

from . import gen_graph, gen_knap, gen_sat, gen_tsp, knap, knap_solvers, tsp, tsp_solvers
from .cnf import Cnf, write_dimacs
from .graph import Graph, write_col
from .knap import Knapsack
from .tsp import Tsp

HEAVY = {"sweep"}


def _light() -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for n in (30, 50, 70):
        for seed in range(3):
            specs.append({"id": f"thr-n{n}-s{seed}", "family": "threshold", "params": {"n": n, "seed": seed}, "expected": None})
    for seed in range(2):
        specs.append({"id": f"planted-n60-s{seed}", "family": "planted", "params": {"n": 60, "m": 240, "seed": seed}, "expected": "SAT"})
    for number, (bp, bq), expected in ((15, (3, 3), "SAT"), (21, (3, 3), "SAT"), (143, (4, 4), "SAT"), (13, (3, 3), "UNSAT"), (61, (3, 3), "UNSAT")):
        specs.append({"id": f"factor-{number}", "family": "factoring", "params": {"n": number, "bits_p": bp, "bits_q": bq}, "expected": expected})
    return specs


def _sweep() -> List[Dict[str, Any]]:
    return [{"id": f"thr-n{n}-s{seed}", "family": "threshold", "params": {"n": n, "seed": seed}, "expected": None}
            for n in (100, 125, 150) for seed in range(5)]


GRAPH_FAMILIES = {"graph"}


def _gspec(name: str, params: Dict[str, Any], kind: str, k: Optional[int], expected: Optional[str]) -> Dict[str, Any]:
    tag = ",".join(f"{key}{value}" for key, value in params.items())
    task = {"kind": kind} if k is None else {"kind": kind, "k": k}
    return {"id": f"{name}[{tag}]-{kind}{'' if k is None else k}", "family": "graph",
            "params": {"graph": name, **params}, "task": task, "expected": expected}


def _graphs() -> List[Dict[str, Any]]:
    s = _gspec
    return [
        s("mycielski", {"k": 3}, "coloring", 3, "SAT"), s("mycielski", {"k": 3}, "coloring", 2, "UNSAT"),
        s("mycielski", {"k": 4}, "coloring", 4, "SAT"), s("mycielski", {"k": 4}, "coloring", 3, "UNSAT"),
        s("queen", {"n": 5}, "coloring", 5, "SAT"), s("queen", {"n": 5}, "coloring", 4, "UNSAT"),
        s("complete", {"n": 6}, "coloring", 6, "SAT"), s("complete", {"n": 6}, "coloring", 5, "UNSAT"),
        s("planted_kcolorable", {"n": 30, "m": 90, "k": 4, "seed": 1}, "coloring", 4, "SAT"),
        s("turan", {"n": 12, "r": 4}, "clique", 4, "SAT"), s("turan", {"n": 12, "r": 4}, "clique", 5, "UNSAT"),
        s("planted_clique", {"n": 40, "p_percent": 30, "size": 8, "seed": 2}, "clique", 8, "SAT"),
        s("gpetersen", {"n": 5, "k": 2}, "hamcycle", None, "UNSAT"),
        s("gpetersen", {"n": 6, "k": 2}, "hamcycle", None, "SAT"),
        s("gpetersen", {"n": 7, "k": 2}, "hamcycle", None, "SAT"),
        s("planted_ham", {"n": 20, "extra": 10, "seed": 4}, "hamcycle", None, "SAT"),
        s("cycle", {"n": 8}, "hamcycle", None, "SAT"),
        s("complete", {"n": 6}, "hamcycle", None, "SAT"),
    ]


OPT_FAMILIES = {"tsp", "knapsack"}


def _tspec(n: int, seed: int, bound: int, expected: Optional[str]) -> Dict[str, Any]:
    return {"id": f"tsp-n{n}-s{seed}-le{bound}", "family": "tsp", "params": {"n": n, "seed": seed, "box": 1000},
            "task": {"kind": "tsp", "bound": bound}, "expected": expected}


def _kspec(family: str, n: int, r: int, seed: int, target: int, expected: Optional[str]) -> Dict[str, Any]:
    return {"id": f"knap-{family}-n{n}-s{seed}-ge{target}", "family": "knapsack",
            "params": {"family": family, "n": n, "r": r, "seed": seed},
            "task": {"kind": "knapsack", "target": target}, "expected": expected}


def _optimization() -> List[Dict[str, Any]]:
    t, k = _tspec, _kspec
    return [
        # n <= 13: the optimum is known from the exact DP; bound = optimum is a yes, optimum - 1 is a no
        t(8, 1, 2854, "SAT"), t(8, 1, 2853, "UNSAT"), t(9, 2, 2949, "SAT"), t(9, 2, 2948, "UNSAT"),
        t(10, 3, 2838, "SAT"), t(10, 3, 2837, "UNSAT"), t(11, 4, 3206, "SAT"), t(11, 4, 3205, "UNSAT"),
        t(12, 5, 3471, "SAT"), t(12, 5, 3470, "UNSAT"),
        # n > 13: the answer rests on a verified tour or a verified lower bound; between the two it is not known
        t(14, 6, 3366, "SAT"), t(14, 6, 3365, "UNSAT"), t(20, 7, 3990, "SAT"), t(20, 7, 3989, "UNSAT"),
        t(30, 8, 4511, "SAT"), t(30, 8, 4454, "UNSAT"), t(30, 8, 4480, None),
        k("uncorrelated", 30, 500, 1, 6874, "SAT"), k("uncorrelated", 30, 500, 1, 6875, "UNSAT"), k("uncorrelated", 30, 500, 1, 6960, "UNSAT"),
        k("weakly_correlated", 30, 500, 2, 4115, "SAT"), k("weakly_correlated", 30, 500, 2, 4133, "UNSAT"),
        k("strongly_correlated", 25, 200, 5, 1630, "SAT"), k("strongly_correlated", 25, 200, 5, 1631, "UNSAT"),
        k("strongly_correlated", 25, 200, 5, 1645, "UNSAT"),
        k("subset_sum", 25, 1000, 4, 5150, "SAT"), k("subset_sum", 25, 1000, 4, 5151, "UNSAT"),
    ]


_SUITES = {"light": _light, "sweep": _sweep, "graphs": _graphs, "optimization": _optimization}


@lru_cache(maxsize=None)
def _tsp_facts(n: int, seed: int, box: int) -> Tuple[Tsp, Optional[int], int, int]:
    """(instance, exact optimum if n is small enough, heuristic tour length, verified lower bound)."""
    inst = gen_tsp.random_euclid(n, seed=seed, box=box)
    heuristic = tsp.verify_tour(inst, tsp_solvers.nn_two_opt(inst, 20).witness)
    pi = tsp_solvers.optimise_potentials(inst, upper=heuristic, deadline_s=20)
    bound = tsp.lower_bound(inst, pi)
    exact = tsp_solvers.held_karp(inst)[0] if n <= tsp_solvers.MAX_DP_N else None
    if exact is not None and not bound <= exact <= heuristic:
        raise AssertionError(f"inconsistent TSP facts for n={n} seed={seed}: bound {bound}, optimum {exact}, heuristic {heuristic}")
    return inst, exact, heuristic, bound


@lru_cache(maxsize=None)
def _knapsack_facts(family: str, n: int, r: int, seed: int) -> Tuple[Knapsack, int, Fraction]:
    inst = gen_knap.generate(family, n, r, seed=seed)
    return inst, knap_solvers.dp_optimum(inst)[0], knap.fractional_upper_bound(inst)


def build_opt_instance(spec: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
    """Rebuild a TSP or knapsack instance and the answer that exact computation or verified evidence supports."""
    family, p, task = spec.get("family"), spec["params"], spec["task"]
    if family == "tsp":
        inst, exact, heuristic, bound = _tsp_facts(p["n"], p["seed"], p["box"])
        limit = task["bound"]
        if exact is not None:
            truth: Optional[str] = "SAT" if exact <= limit else "UNSAT"
        elif heuristic <= limit:
            truth = "SAT"  # a tour of that length exists (verified)
        elif bound > limit:
            truth = "UNSAT"  # a verified lower bound exceeds the limit
        else:
            truth = None  # between the lower bound and the best tour found: not known
    elif family == "knapsack":
        inst, optimum, lp = _knapsack_facts(p["family"], p["n"], p["r"], p["seed"])
        truth = "SAT" if optimum >= task["target"] else "UNSAT"
    else:
        raise ValueError(f"not an optimisation spec: {family!r}")
    if spec.get("expected") != truth:
        raise ValueError(f"instance {spec.get('id')!r}: claimed answer {spec.get('expected')!r} but the computation supports {truth!r}")
    return inst, truth


def graph_truth(name: str, params: Dict[str, Any], task: Dict[str, Any]) -> Optional[str]:
    """The answer a theorem or the construction guarantees for this task; None when nothing is guaranteed."""
    facts = gen_graph.known((name, params))
    kind, k = task["kind"], task.get("k")
    if kind == "coloring":
        if "chi" in facts:
            return "SAT" if k >= facts["chi"] else "UNSAT"
        if name == "planted_kcolorable" and k >= params["k"]:
            return "SAT"
    elif kind == "clique":
        if "omega" in facts:
            return "SAT" if k <= facts["omega"] else "UNSAT"
        if name == "planted_clique" and k <= params["size"]:
            return "SAT"
    elif kind == "hamcycle":
        if name in ("planted_ham",) or (name in ("complete", "cycle") and params["n"] >= 3):
            return "SAT"
        if name == "gpetersen":
            return "SAT" if gen_graph.petersen_is_hamiltonian(params["n"], params["k"]) else "UNSAT"
    return None


def build_graph_instance(spec: Dict[str, Any]) -> Tuple[Graph, Optional[str]]:
    if spec.get("family") not in GRAPH_FAMILIES:
        raise ValueError(f"not a graph spec: {spec.get('family')!r}")
    params = dict(spec["params"])
    name = params.pop("graph")
    graph = gen_graph.build((name, params))
    truth = graph_truth(name, params, spec["task"])
    if spec.get("expected") != truth:
        raise ValueError(f"instance {spec.get('id')!r}: claimed answer {spec.get('expected')!r} but the generator knows {truth!r}")
    return graph, truth


def suite_names() -> List[str]:
    return sorted(_SUITES)


def is_heavy(name: str) -> bool:
    return name in HEAVY


def suite_specs(name: str) -> List[Dict[str, Any]]:
    if name not in _SUITES:
        raise ValueError(f"unknown suite {name!r}; known: {', '.join(suite_names())}")
    return _SUITES[name]()


def build_instance(spec: Dict[str, Any]) -> Tuple[Cnf, Optional[str]]:
    family, params = spec.get("family"), dict(spec.get("params") or {})
    claimed = spec.get("expected")
    if family == "threshold":
        formula, truth = gen_sat.threshold_instance(params["n"], seed=params["seed"]), None
    elif family == "random3sat":
        formula, truth = gen_sat.random_ksat(params["n"], params["m"], 3, seed=params["seed"]), None
    elif family == "planted":
        formula, _ = gen_sat.planted_ksat(params["n"], params["m"], 3, seed=params["seed"])
        truth = "SAT"
    elif family == "factoring":
        formula, truth = gen_sat.factoring_cnf(params["n"], bits_p=params["bits_p"], bits_q=params["bits_q"])
    else:
        raise ValueError(f"unknown family {family!r}")
    if claimed != truth:
        raise ValueError(f"instance {spec.get('id')!r}: claimed answer {claimed!r} but the generator knows {truth!r}")
    return formula, truth


def manifest(name: str) -> List[Dict[str, Any]]:
    entries = []
    for spec in suite_specs(name):
        if spec["family"] in OPT_FAMILIES:
            instance, truth = build_opt_instance(spec)
            text = tsp.write_tsplib(instance) if spec["family"] == "tsp" else instance.to_text()
            entries.append({
                "id": spec["id"], "family": spec["family"], "params": spec["params"], "task": spec["task"], "expected": truth,
                "generator": gen_tsp.GENERATOR_VERSION if spec["family"] == "tsp" else gen_knap.GENERATOR_VERSION,
                "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
            })
            continue
        if spec["family"] in GRAPH_FAMILIES:
            graph, truth = build_graph_instance(spec)
            entries.append({
                "id": spec["id"], "family": spec["family"], "params": spec["params"], "task": spec["task"], "expected": truth,
                "generator": gen_graph.GENERATOR_VERSION, "num_vertices": graph.n, "num_edges": len(graph.edges),
                "sha256": hashlib.sha256(write_col(graph).encode("ascii")).hexdigest(),
            })
            continue
        formula, truth = build_instance(spec)
        entries.append({
            "id": spec["id"], "family": spec["family"], "params": spec["params"], "expected": truth,
            "generator": gen_sat.GENERATOR_VERSION, "num_vars": formula.num_vars, "num_clauses": len(formula.clauses),
            "sha256": hashlib.sha256(write_dimacs(formula).encode("ascii")).hexdigest(),
        })
    return entries
