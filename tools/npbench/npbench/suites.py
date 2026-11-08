"""Benchmark suites: a suite is a list of instance specs; an instance is rebuilt from its spec, never stored.

A spec is ``{"id", "family", "params", "expected"}``. ``expected`` is a claim about the answer. The generator is the
authority: if it knows the answer (planted, factoring) a different claim is refused, and if it does not (random,
threshold) a claim is refused too, so a suite file can never smuggle in an unverified "known answer".
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from . import gen_graph, gen_sat
from .cnf import Cnf, write_dimacs
from .graph import Graph, write_col

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


_SUITES = {"light": _light, "sweep": _sweep, "graphs": _graphs}


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
