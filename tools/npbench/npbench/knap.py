"""Knapsack for the benchmark (subset sum is the case profit = weight): instance, verifier, exact LP bound.

``verify_selection`` accepts a selection only if the indices are distinct integers in range, the weight fits the
capacity and the profit reaches the target. ``fractional_upper_bound`` is the Dantzig bound in exact rational
arithmetic: no selection can have a profit above it, so a target above it has no solution (a certified "no").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence, Tuple


@dataclass(frozen=True)
class Knapsack:
    items: Tuple[Tuple[int, int], ...]  # (weight, profit)
    capacity: int

    def __post_init__(self) -> None:
        if not isinstance(self.capacity, int) or isinstance(self.capacity, bool) or self.capacity < 0:
            raise ValueError("capacity must be a non-negative integer")
        for w, p in self.items:
            if not all(isinstance(x, int) and not isinstance(x, bool) for x in (w, p)) or w < 1 or p < 0:
                raise ValueError("weights must be integers >= 1 and profits integers >= 0")

    def to_text(self) -> str:
        return json.dumps({"capacity": self.capacity, "items": [list(i) for i in self.items]}, sort_keys=True, separators=(",", ":")) + "\n"


def verify_selection(inst: Knapsack, chosen: Sequence[int], target: int) -> bool:
    if not isinstance(chosen, (list, tuple)):
        return False
    if any(not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(inst.items) for i in chosen):
        return False
    if len(set(chosen)) != len(chosen):
        return False
    weight = sum(inst.items[i][0] for i in chosen)
    profit = sum(inst.items[i][1] for i in chosen)
    return weight <= inst.capacity and profit >= target


def fractional_upper_bound(inst: Knapsack) -> Fraction:
    order = sorted(inst.items, key=lambda it: Fraction(it[1], it[0]), reverse=True)
    room = inst.capacity
    bound = Fraction(0)
    for w, p in order:
        if w <= room:
            room -= w
            bound += p
        else:
            bound += Fraction(p * room, w)
            break
    return bound
