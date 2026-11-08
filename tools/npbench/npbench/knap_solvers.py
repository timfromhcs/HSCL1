"""Knapsack solvers. Every answer is verified by ``knap`` code in ``opt_runner``.

* ``dp_optimum``: exact dynamic programme over the capacity with witness reconstruction. As a decision answer a "no"
  from it is not an independent certificate, so the registry wrapper reports UNKNOWN for it.
* ``greedy``: density order; a selection, never a proof.
* ``solve_ub``: claims "no" when the target exceeds the exact fractional bound; the runner recomputes that bound itself.
"""

from __future__ import annotations

from fractions import Fraction
from typing import List, Tuple

from .knap import Knapsack, fractional_upper_bound
from .opt_types import OptResult

MAX_DP_CAPACITY = 300_000


def dp_optimum(inst: Knapsack) -> Tuple[int, List[int]]:
    cap = inst.capacity
    if cap > MAX_DP_CAPACITY:
        raise ValueError(f"the exact DP is limited to capacity <= {MAX_DP_CAPACITY}")
    n = len(inst.items)
    table = [[0] * (cap + 1)]
    for w, p in inst.items:
        prev = table[-1]
        row = prev[:]
        for c in range(w, cap + 1):
            cand = prev[c - w] + p
            if cand > row[c]:
                row[c] = cand
        table.append(row)
    value, c, chosen = table[n][cap], cap, []
    for i in range(n, 0, -1):
        if table[i][c] != table[i - 1][c]:
            chosen.append(i - 1)
            c -= inst.items[i - 1][0]
    return value, sorted(chosen)


def greedy(inst: Knapsack, target: int) -> OptResult:
    order = sorted(range(len(inst.items)), key=lambda i: Fraction(inst.items[i][1], inst.items[i][0]), reverse=True)
    room, chosen, profit = inst.capacity, [], 0
    for i in order:
        w, p = inst.items[i]
        if w <= room:
            room -= w
            chosen.append(i)
            profit += p
    if profit >= target:
        return OptResult("SAT", sorted(chosen), None, None, len(order), f"greedy profit {profit}")
    return OptResult("UNKNOWN", None, None, None, len(order), f"greedy profit {profit} is below the target")


# ---- registry wrappers: (instance, task, deadline_s) -> OptResult ---------------------------------
def solve_dp(inst: Knapsack, task: dict, deadline_s: float) -> OptResult:
    if inst.capacity > MAX_DP_CAPACITY:
        return OptResult("UNKNOWN", None, None, None, 0, "capacity too large for the exact DP")
    value, chosen = dp_optimum(inst)
    if value >= task["target"]:
        return OptResult("SAT", chosen, None, None, len(inst.items), f"optimum {value}")
    return OptResult("UNKNOWN", None, None, None, len(inst.items), f"exact DP finished: optimum {value} is below the target; no independent certificate")


def solve_greedy(inst: Knapsack, task: dict, deadline_s: float) -> OptResult:
    return greedy(inst, task["target"])


def solve_ub(inst: Knapsack, task: dict, deadline_s: float) -> OptResult:
    bound = fractional_upper_bound(inst)
    if Fraction(task["target"]) > bound:
        return OptResult("UNSAT", None, "LP_BOUND", None, 1, f"fractional bound {float(bound):.3f} is below the target")
    return OptResult("UNKNOWN", None, None, None, 1, f"fractional bound {float(bound):.3f} does not exclude the target")
