"""Independent RUP refutation checker. Shares no code with any solver in this package.

A proof is a list of lemma clauses. Each lemma must follow by unit propagation from the formula plus the lemmas
before it after assuming the lemma false (reverse unit propagation); the last lemma must be the empty clause.
No deletions and no RAT: it checks the proofs the CDCL baseline writes, nothing more. A DRAT checker for external
solvers is a separate, later item.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .cnf import Cnf


def _conflict_after_assuming(db: List[Sequence[int]], assumptions: Iterable[int]) -> bool:
    value: dict[int, bool] = {}
    for lit in assumptions:
        var, want = abs(lit), lit > 0
        if value.get(var, want) != want:
            return True
        value[var] = want
    changed = True
    while changed:
        changed = False
        for clause in db:
            open_lit = 0
            open_count = 0
            satisfied = False
            for lit in clause:
                known = value.get(abs(lit))
                if known is None:
                    open_count += 1
                    open_lit = lit
                elif known == (lit > 0):
                    satisfied = True
                    break
            if satisfied:
                continue
            if open_count == 0:
                return True
            if open_count == 1:
                value[abs(open_lit)] = open_lit > 0
                changed = True
    return False


def check_rup(formula: Cnf, proof: Sequence[Sequence[int]] | None) -> bool:
    if not proof:
        return False
    db: List[Sequence[int]] = [tuple(c) for c in formula.clauses]
    if any(len(c) == 0 for c in db):
        return True  # the formula itself contains the empty clause
    for lemma in proof:
        lemma = tuple(lemma)
        if any(not isinstance(x, int) or isinstance(x, bool) or x == 0 or abs(x) > formula.num_vars for x in lemma):
            return False
        if not _conflict_after_assuming(db, (-x for x in lemma)):
            return False
        if not lemma:
            return True
        db.append(lemma)
    return False
