"""Graph generators with known values. A value is claimed only where it is a theorem or follows from the construction.

Known values (``known``):
* Mycielski graphs M_k (k >= 2): chromatic number k, clique number 2 (they are triangle free); Mycielski's construction.
* Queen graphs n x n with gcd(n, 6) = 1: chromatic number n (a classical result for such n), clique number n (one row).
  Other n are **not** claimed: the DIMACS tables list best-known values for them, which are not theorems here.
* Turan graphs T(n, r) (complete r-partite, balanced): chromatic number = clique number = r.
* Complete graphs K_n: both n.
* Planted generators give one-sided facts only (a colouring, a clique or a Hamiltonian cycle exists), recorded as such.
* Generalised Petersen graphs GP(n, k): Hamiltonian unless k = 2 and n = 5 (mod 6) (Alspach 1983); the table is checked
  against exhaustive search for small n in the tests.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .graph import Graph, make_graph

GENERATOR_VERSION = "npbench.gen_graph/1"


def complete(n: int) -> Graph:
    return make_graph(n, ((u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1)))


def cycle(n: int) -> Graph:
    if n < 3:
        raise ValueError("a cycle needs at least 3 vertices")
    return make_graph(n, ((i, i % n + 1) for i in range(1, n + 1)))


def mycielskian(g: Graph) -> Graph:
    n = g.n
    edges = list(g.edges)
    for u, v in g.edges:
        edges.append((u, n + v))
        edges.append((v, n + u))
    edges.extend((n + i, 2 * n + 1) for i in range(1, n + 1))
    return make_graph(2 * n + 1, edges)


def mycielski(k: int) -> Graph:
    if k < 2:
        raise ValueError("k must be at least 2")
    g = complete(2)
    for _ in range(k - 2):
        g = mycielskian(g)
    return g


def queen(n: int) -> Graph:
    if n < 1:
        raise ValueError("n must be positive")
    cells = [(r, c) for r in range(n) for c in range(n)]
    index = {cell: i + 1 for i, cell in enumerate(cells)}
    edges = []
    for (r1, c1) in cells:
        for (r2, c2) in cells:
            if index[(r1, c1)] < index[(r2, c2)] and (r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2)):
                edges.append((index[(r1, c1)], index[(r2, c2)]))
    return make_graph(n * n, edges)


def turan(n: int, r: int) -> Graph:
    if r < 1 or n < r:
        raise ValueError("need 1 <= r <= n")
    return make_graph(n, ((u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1) if (u - 1) % r != (v - 1) % r))


def generalized_petersen(n: int, k: int) -> Graph:
    if n < 3 or not 1 <= k or 2 * k >= n:
        raise ValueError("need n >= 3 and 1 <= k < n/2")
    edges = []
    for i in range(1, n + 1):
        edges.append((i, i % n + 1))  # outer cycle
        edges.append((i, n + i))  # spoke
        edges.append((n + i, n + (i - 1 + k) % n + 1))  # inner star polygon
    return make_graph(2 * n, edges)


def petersen_is_hamiltonian(n: int, k: int) -> bool:
    """Alspach: GP(n, k) is non-Hamiltonian exactly when it is isomorphic to GP(n, 2) with n = 5 (mod 6).

    GP(n, k) and GP(n, l) are isomorphic when k = +-l or k * l = +-1 (mod n); for n odd and k < n/2 the only k other
    than 2 that is isomorphic to 2 is (n - 1) / 2, because 2 * (n - 1) / 2 = -1 (mod n). The tests check this table
    against an exhaustive search for every 5 <= n <= 12 (the case GP(11, 5) was a real miss of the plain statement).
    """
    return not (n % 6 == 5 and k in (2, (n - 1) // 2))


def planted_kcolorable(n: int, m: int, k: int, *, seed: int) -> Tuple[Graph, Dict[int, int]]:
    if k < 2 or n < k:
        raise ValueError("bad parameters")
    rng = random.Random(seed)
    order = list(range(1, n + 1))
    rng.shuffle(order)
    colors = {v: i % k for i, v in enumerate(order)}  # balanced classes, every colour used when n >= k
    possible = [(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1) if colors[u] != colors[v]]
    if m > len(possible):
        raise ValueError("more edges requested than the colouring allows")
    return make_graph(n, rng.sample(possible, m)), colors


def planted_clique(n: int, p: float, size: int, *, seed: int) -> Tuple[Graph, List[int]]:
    if not 0 <= p <= 1 or size < 2 or size > n:
        raise ValueError("bad parameters")
    rng = random.Random(seed)
    members = sorted(rng.sample(range(1, n + 1), size))
    edges = {(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1) if rng.random() < p}
    edges |= {(a, b) for i, a in enumerate(members) for b in members[i + 1:]}
    return make_graph(n, edges), members


def planted_ham(n: int, extra: int, *, seed: int) -> Tuple[Graph, List[int]]:
    if n < 3:
        raise ValueError("n must be at least 3")
    rng = random.Random(seed)
    order = list(range(1, n + 1))
    rng.shuffle(order)
    edges = {tuple(sorted((a, b))) for a, b in zip(order, order[1:] + order[:1])}
    attempts = 0
    while extra > 0 and attempts < 50 * (extra + 1):
        attempts += 1
        u, v = rng.sample(range(1, n + 1), 2)
        key = (u, v) if u < v else (v, u)
        if key not in edges:
            edges.add(key)
            extra -= 1
    return make_graph(n, edges), order


def known(descriptor: Tuple[str, Dict[str, int]]) -> Dict[str, int]:
    """Theorem-backed values for a named construction; an empty dict means: nothing is claimed."""
    name, p = descriptor
    if name == "mycielski":
        return {"chi": p["k"], "omega": 2}
    if name == "queen":
        return {"chi": p["n"], "omega": p["n"]} if math.gcd(p["n"], 6) == 1 else {}
    if name == "turan":
        return {"chi": p["r"], "omega": p["r"]}
    if name == "complete":
        return {"chi": p["n"], "omega": p["n"]}
    return {}


def build(descriptor: Tuple[str, Dict[str, int]]) -> Graph:
    """Rebuild a graph from its descriptor (name and parameters)."""
    name, p = descriptor
    if name == "mycielski":
        return mycielski(p["k"])
    if name == "queen":
        return queen(p["n"])
    if name == "turan":
        return turan(p["n"], p["r"])
    if name == "complete":
        return complete(p["n"])
    if name == "cycle":
        return cycle(p["n"])
    if name == "gpetersen":
        return generalized_petersen(p["n"], p["k"])
    if name == "planted_kcolorable":
        return planted_kcolorable(p["n"], p["m"], p["k"], seed=p["seed"])[0]
    if name == "planted_clique":
        return planted_clique(p["n"], p["p_percent"] / 100.0, p["size"], seed=p["seed"])[0]
    if name == "planted_ham":
        return planted_ham(p["n"], p["extra"], seed=p["seed"])[0]
    raise ValueError(f"unknown graph {name!r}")
