"""Knapsack instance families after Pisinger ("Where are the hard knapsack problems?", C&OR 2005): the families whose
LP relaxation is a poor guide are the strongly correlated ones. Weights are uniform in [1, R]; capacity is half the total
weight. Only the four families named in the benchmark are generated; this is not a copy of Pisinger's code.
"""

from __future__ import annotations

import random

from .knap import Knapsack

GENERATOR_VERSION = "npbench.gen_knap/1"
FAMILIES = ("uncorrelated", "weakly_correlated", "strongly_correlated", "subset_sum")


def generate(family: str, n: int, r: int, *, seed: int) -> Knapsack:
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; known: {', '.join(FAMILIES)}")
    if n < 2 or r < 10:
        raise ValueError("need n >= 2 and R >= 10")
    rng = random.Random(seed)
    items = []
    for _ in range(n):
        w = rng.randint(1, r)
        if family == "uncorrelated":
            p = rng.randint(1, r)
        elif family == "weakly_correlated":
            p = max(1, w + rng.randint(-(r // 10), r // 10))
        elif family == "strongly_correlated":
            p = w + r // 10
        else:
            p = w
        items.append((w, p))
    return Knapsack(tuple(items), sum(w for w, _ in items) // 2)
