"""WalkSAT local search. Incomplete by nature: it can find models and can never prove UNSAT, so it answers SAT or UNKNOWN."""

from __future__ import annotations

import random
import time

from ..cnf import Cnf, verify_model
from .cdcl import Result


def solve(formula: Cnf, *, deadline_s: float, seed: int = 0, noise: float = 0.5, max_flips: int = 5_000_000) -> Result:
    deadline = time.perf_counter() + float(deadline_s)
    rng = random.Random(seed)
    n = formula.num_vars
    if any(len(c) == 0 for c in formula.clauses):
        return Result("UNKNOWN", None, None, 0, "empty clause; local search cannot decide")
    assign = [False] + [rng.random() < 0.5 for _ in range(n)]
    clauses = [list(c) for c in formula.clauses]
    occurs: dict[int, list[int]] = {}
    for ci, clause in enumerate(clauses):
        for lit in clause:
            occurs.setdefault(abs(lit), []).append(ci)

    def true_count(ci: int) -> int:
        return sum(1 for lit in clauses[ci] if assign[abs(lit)] == (lit > 0))

    counts = [true_count(ci) for ci in range(len(clauses))]
    unsat = {ci for ci, c in enumerate(counts) if c == 0}
    flips = 0
    while unsat and flips < max_flips:
        if flips % 256 == 0 and time.perf_counter() > deadline:
            return Result("UNKNOWN", None, None, flips, "deadline reached")
        flips += 1
        ci = rng.choice(tuple(unsat))
        clause = clauses[ci]

        def breaks(var: int) -> int:
            return sum(1 for cj in occurs[var] if counts[cj] == 1 and any(abs(l) == var and assign[var] == (l > 0) for l in clauses[cj]))

        scored = [(breaks(abs(lit)), abs(lit)) for lit in clause]
        best = min(s for s, _ in scored)
        if best > 0 and rng.random() < noise:
            var = abs(rng.choice(clause))  # random walk step
        else:
            var = rng.choice([v for s, v in scored if s == best])  # greedy step
        assign[var] = not assign[var]
        for cj in occurs[var]:
            counts[cj] = true_count(cj)
            if counts[cj] == 0:
                unsat.add(cj)
            else:
                unsat.discard(cj)
    if unsat:
        return Result("UNKNOWN", None, None, flips, "flip budget exhausted")
    model = {v: assign[v] for v in range(1, n + 1)}
    return Result("SAT", model, None, flips) if verify_model(formula, model) else Result("UNKNOWN", None, None, flips, "internal model check failed")
