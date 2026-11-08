"""Benchmark suites: a suite is a list of instance specs; an instance is rebuilt from its spec, never stored.

A spec is ``{"id", "family", "params", "expected"}``. ``expected`` is a claim about the answer. The generator is the
authority: if it knows the answer (planted, factoring) a different claim is refused, and if it does not (random,
threshold) a claim is refused too, so a suite file can never smuggle in an unverified "known answer".
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from . import gen_sat
from .cnf import Cnf, write_dimacs

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


_SUITES = {"light": _light, "sweep": _sweep}


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
        formula, truth = build_instance(spec)
        entries.append({
            "id": spec["id"], "family": spec["family"], "params": spec["params"], "expected": truth,
            "generator": gen_sat.GENERATOR_VERSION, "num_vars": formula.num_vars, "num_clauses": len(formula.clauses),
            "sha256": hashlib.sha256(write_dimacs(formula).encode("ascii")).hexdigest(),
        })
    return entries
