"""A small CDCL solver in pure Python: two watched literals, first-UIP learning with backjumping, VSIDS-style
activity, phase saving, Luby restarts, and a RUP proof of every UNSAT answer.

It is a correctness baseline for the benchmark harness, not a competitor to CaDiCaL or Kissat. No clause deletion and
no learned-clause minimisation, so memory grows with the number of conflicts; the deadline bounds the run. A timeout
is ``UNKNOWN``; this module never reports UNSAT without a proof, and the runner still checks that proof independently.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..cnf import Cnf


@dataclass
class Result:
    status: str  # "SAT" | "UNSAT" | "UNKNOWN"
    model: Optional[Dict[int, bool]]
    proof: Optional[List[List[int]]]
    conflicts: int
    note: str = ""


def _luby(i: int) -> int:
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    while True:
        if i == (1 << k) - 1:
            return 1 << (k - 1)
        i -= (1 << (k - 1)) - 1
        k = 1
        while (1 << k) - 1 < i:
            k += 1


class _Solver:
    def __init__(self, formula: Cnf, deadline: float) -> None:
        self.n = formula.num_vars
        self.deadline = deadline
        self.val = [0] * (self.n + 1)  # 1 true, -1 false, 0 open
        self.level = [0] * (self.n + 1)
        self.reason: List[Optional[int]] = [None] * (self.n + 1)
        self.trail: List[int] = []
        self.lim: List[int] = []
        self.qhead = 0
        self.clauses: List[List[int]] = []
        self.watches: Dict[int, List[int]] = {}
        self.activity = [0.0] * (self.n + 1)
        self.inc = 1.0
        self.phase = [False] * (self.n + 1)
        self.proof: List[List[int]] = []
        self.conflicts = 0
        self.ok = True
        for clause in formula.clauses:
            if not self._add_original(clause):
                self.ok = False
                break

    # -- helpers --------------------------------------------------------------------------
    def _value(self, lit: int) -> int:
        v = self.val[abs(lit)]
        return v if lit > 0 else -v

    def _enqueue(self, lit: int, reason: Optional[int]) -> bool:
        current = self._value(lit)
        if current != 0:
            return current == 1
        var = abs(lit)
        self.val[var] = 1 if lit > 0 else -1
        self.level[var] = len(self.lim)
        self.reason[var] = reason
        self.trail.append(lit)
        return True

    def _watch(self, lit: int, index: int) -> None:
        self.watches.setdefault(lit, []).append(index)

    def _add_original(self, clause) -> bool:
        lits = list(dict.fromkeys(clause))
        if any(-x in lits for x in lits):
            return True  # tautology
        if not lits:
            return False
        if len(lits) == 1:
            return self._enqueue(lits[0], None)
        self.clauses.append(lits)
        index = len(self.clauses) - 1
        self._watch(lits[0], index)
        self._watch(lits[1], index)
        return True

    # -- propagation ----------------------------------------------------------------------
    def _propagate(self) -> Optional[int]:
        while self.qhead < len(self.trail):
            lit = self.trail[self.qhead]
            self.qhead += 1
            falsified = -lit
            watching = self.watches.get(falsified, [])
            keep: List[int] = []
            i = 0
            while i < len(watching):
                ci = watching[i]
                i += 1
                c = self.clauses[ci]
                if c[0] == falsified:
                    c[0], c[1] = c[1], c[0]
                if self._value(c[0]) == 1:
                    keep.append(ci)
                    continue
                moved = False
                for k in range(2, len(c)):
                    if self._value(c[k]) != -1:
                        c[1], c[k] = c[k], c[1]
                        self._watch(c[1], ci)
                        moved = True
                        break
                if moved:
                    continue
                keep.append(ci)
                if self._value(c[0]) == -1:
                    keep.extend(watching[i:])
                    self.watches[falsified] = keep
                    self.qhead = len(self.trail)
                    return ci
                self._enqueue(c[0], ci)
            self.watches[falsified] = keep
        return None

    # -- conflict analysis ----------------------------------------------------------------
    def _bump(self, var: int) -> None:
        self.activity[var] += self.inc
        if self.activity[var] > 1e100:
            self.activity = [a * 1e-100 for a in self.activity]
            self.inc *= 1e-100

    def _analyze(self, conflict: int):
        seen = set()
        learnt: List[int] = [0]
        counter = 0
        p = 0
        index = len(self.trail) - 1
        current = len(self.lim)
        ci: Optional[int] = conflict
        while True:
            assert ci is not None
            for q in self.clauses[ci]:
                if q == p:
                    continue
                var = abs(q)
                if var not in seen and self.level[var] > 0:
                    seen.add(var)
                    self._bump(var)
                    if self.level[var] >= current:
                        counter += 1
                    else:
                        learnt.append(q)
            while abs(self.trail[index]) not in seen:
                index -= 1
            p = self.trail[index]
            index -= 1
            ci = self.reason[abs(p)]
            seen.discard(abs(p))
            counter -= 1
            if counter == 0:
                break
        learnt[0] = -p
        if len(learnt) == 1:
            return learnt, 0
        best = max(range(1, len(learnt)), key=lambda t: self.level[abs(learnt[t])])
        learnt[1], learnt[best] = learnt[best], learnt[1]
        return learnt, self.level[abs(learnt[1])]

    def _backjump(self, level: int) -> None:
        if len(self.lim) <= level:
            return
        target = self.lim[level]
        for lit in self.trail[target:]:
            var = abs(lit)
            self.phase[var] = lit > 0
            self.val[var] = 0
            self.reason[var] = None
        del self.trail[target:]
        del self.lim[level:]
        self.qhead = len(self.trail)

    def _decide(self) -> int:
        best, best_act = 0, -1.0
        for var in range(1, self.n + 1):
            if self.val[var] == 0 and self.activity[var] > best_act:
                best, best_act = var, self.activity[var]
        return best

    # -- main loop ------------------------------------------------------------------------
    def run(self) -> Result:
        if not self.ok:
            return Result("UNSAT", None, [[]], 0, "empty clause or conflicting units in the input")
        restart_unit, restarts, budget = 64, 1, 64
        since = 0
        ticks = 0
        while True:
            conflict = self._propagate()
            ticks += 1
            if ticks % 128 == 0 and time.perf_counter() > self.deadline:
                return Result("UNKNOWN", None, None, self.conflicts, "deadline reached")
            if conflict is not None:
                self.conflicts += 1
                since += 1
                if not self.lim:
                    self.proof.append([])
                    return Result("UNSAT", None, self.proof, self.conflicts)
                learnt, back = self._analyze(conflict)
                self.proof.append(list(learnt))
                self._backjump(back)
                if len(learnt) == 1:
                    self._enqueue(learnt[0], None)
                else:
                    self.clauses.append(learnt)
                    index = len(self.clauses) - 1
                    self._watch(learnt[0], index)
                    self._watch(learnt[1], index)
                    self._enqueue(learnt[0], index)
                self.inc /= 0.95
                continue
            if since >= budget:
                restarts += 1
                budget = restart_unit * _luby(restarts)
                since = 0
                self._backjump(0)
                continue
            var = self._decide()
            if var == 0:
                model = {v: self.val[v] == 1 for v in range(1, self.n + 1)}
                return Result("SAT", model, None, self.conflicts)
            self.lim.append(len(self.trail))
            self._enqueue(var if self.phase[var] else -var, None)


def solve(formula: Cnf, *, deadline_s: float, seed: int = 0) -> Result:
    """``deadline_s`` is a wall-clock budget in seconds from now. ``seed`` is accepted for a uniform solver signature."""
    return _Solver(formula, time.perf_counter() + float(deadline_s)).run()
