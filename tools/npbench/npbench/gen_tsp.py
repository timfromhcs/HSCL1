"""TSP instance generators."""

from __future__ import annotations

import random

from .tsp import Tsp

GENERATOR_VERSION = "npbench.gen_tsp/1"


def random_euclid(n: int, *, seed: int, box: int = 1000) -> Tsp:
    """n points with integer coordinates drawn uniformly from [0, box]^2 (TSPLIB EUC_2D distances)."""
    if n < 3:
        raise ValueError("a tour needs at least 3 points")
    if box < 1:
        raise ValueError("box must be positive")
    rng = random.Random(seed)
    return Tsp(tuple((rng.randint(0, box), rng.randint(0, box)) for _ in range(n)))
