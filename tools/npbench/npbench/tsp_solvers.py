"""TSP solvers. Each answer is verified by ``tsp`` code in ``opt_runner``.

* ``held_karp``: exact dynamic programme over subsets (n <= 13). It *computes* the optimum; as a decision answer a "no"
  from it is not an independent certificate, so the registry wrapper reports UNKNOWN for it.
* ``nn_two_opt``: nearest neighbour from every start followed by 2-opt; a tour, never a proof.
* ``optimise_potentials``: subgradient ascent on the Lagrangian 1-tree bound; returns integer potentials that the
  verifier ``tsp.lower_bound`` can check.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from . import tsp as T
from .opt_types import OptResult
from .tsp import Tsp

MAX_DP_N = 13


def held_karp(inst: Tsp) -> Tuple[int, List[int]]:
    n = inst.n
    if n > MAX_DP_N:
        raise ValueError(f"the exact DP is limited to n <= {MAX_DP_N}")
    d = inst.matrix()
    m = n - 1  # vertices 1..n-1 are mapped to bits 0..m-1; vertex 0 is the start
    inf = float("inf")
    dp = [[inf] * m for _ in range(1 << m)]
    parent = [[-1] * m for _ in range(1 << m)]
    for j in range(m):
        dp[1 << j][j] = d[0][j + 1]
    for mask in range(1, 1 << m):
        row = dp[mask]
        for j in range(m):
            cur = row[j]
            if cur == inf or not (mask >> j) & 1:
                continue
            for k in range(m):
                if (mask >> k) & 1:
                    continue
                nm = mask | (1 << k)
                cand = cur + d[j + 1][k + 1]
                if cand < dp[nm][k]:
                    dp[nm][k] = cand
                    parent[nm][k] = j
    full = (1 << m) - 1
    best, last = min((dp[full][j] + d[j + 1][0], j) for j in range(m))
    order = []
    mask, j = full, last
    while j != -1:
        order.append(j + 1)
        pj = parent[mask][j]
        mask ^= 1 << j
        j = pj
    tour = [0] + order[::-1]
    return int(best), tour


def nn_two_opt(inst: Tsp, deadline_s: float) -> OptResult:
    n = inst.n
    d = inst.matrix()
    deadline = time.perf_counter() + float(deadline_s)

    def length(t: List[int]) -> int:
        return sum(d[t[i]][t[(i + 1) % n]] for i in range(n))

    best_tour: Optional[List[int]] = None
    best_len = None
    for start in range(n):
        if time.perf_counter() > deadline and best_tour is not None:
            break
        tour = [start]
        left = set(range(n)) - {start}
        while left:
            nxt = min(left, key=lambda v: (d[tour[-1]][v], v))
            tour.append(nxt)
            left.discard(nxt)
        improved = True
        while improved:
            improved = False
            for i in range(n - 1):
                for j in range(i + 2, n):
                    if i == 0 and j == n - 1:
                        continue
                    a, b, c, e = tour[i], tour[i + 1], tour[j], tour[(j + 1) % n]
                    if d[a][c] + d[b][e] < d[a][b] + d[c][e]:
                        tour[i + 1:j + 1] = reversed(tour[i + 1:j + 1])
                        improved = True
            if time.perf_counter() > deadline:
                break
        cur = length(tour)
        if best_len is None or cur < best_len:
            best_len, best_tour = cur, list(tour)
    return OptResult("SAT", best_tour, None, None, n, f"best tour length {best_len}")


def _one_tree(d: List[List[int]], pi: List[int]) -> Tuple[int, List[int]]:
    """Cost of the 1-tree under potentials pi, and the degree of every vertex (the subgradient is degree - 2)."""
    n = len(d)

    def w(i: int, j: int) -> int:
        return d[i][j] + pi[i] + pi[j]

    in_tree = [False] * n
    best = [None] * n
    link = [-1] * n
    best[1] = 0
    deg = [0] * n
    total = 0
    for _ in range(n - 1):
        u = min((v for v in range(1, n) if not in_tree[v] and best[v] is not None), key=lambda v: best[v])
        in_tree[u] = True
        total += best[u]
        if link[u] != -1:
            deg[u] += 1
            deg[link[u]] += 1
        for v in range(1, n):
            if not in_tree[v]:
                weight = w(u, v)
                if best[v] is None or weight < best[v]:
                    best[v], link[v] = weight, u
    two = sorted(range(1, n), key=lambda j: (w(0, j), j))[:2]
    for j in two:
        total += w(0, j)
        deg[0] += 1
        deg[j] += 1
    return total - 2 * sum(pi), deg


def optimise_potentials(inst: Tsp, upper: int, deadline_s: float, iterations: int = 400) -> List[int]:
    d = inst.matrix()
    n = inst.n
    deadline = time.perf_counter() + float(deadline_s)
    pi = [0] * n
    best_pi, best_lb = list(pi), None
    lam, stale = 2.0, 0
    for _ in range(iterations):
        lb, deg = _one_tree(d, pi)
        if best_lb is None or lb > best_lb:
            best_lb, best_pi, stale = lb, list(pi), 0
        else:
            stale += 1
            if stale >= 15:
                lam, stale = lam / 2, 0
        g2 = sum((x - 2) ** 2 for x in deg)
        if g2 == 0 or lam < 1e-3 or time.perf_counter() > deadline:
            break
        step = lam * max(upper - lb, 1) / g2
        pi = [p + round(step * (x - 2)) for p, x in zip(pi, deg)]
    return best_pi


# ---- registry wrappers: (instance, task, deadline_s) -> OptResult ---------------------------------
def solve_dp(inst: Tsp, task: dict, deadline_s: float) -> OptResult:
    if inst.n > MAX_DP_N:
        return OptResult("UNKNOWN", None, None, None, 0, f"too large for the exact DP (n > {MAX_DP_N})")
    length, tour = held_karp(inst)
    if length <= task["bound"]:
        return OptResult("SAT", tour, None, None, inst.n, f"optimum {length}")
    return OptResult("UNKNOWN", None, None, None, inst.n, f"exact DP finished: optimum {length} is above the bound; no independent certificate")


def solve_nn2opt(inst: Tsp, task: dict, deadline_s: float) -> OptResult:
    res = nn_two_opt(inst, deadline_s)
    length = T.verify_tour(inst, res.witness)
    if length is not None and length <= task["bound"]:
        return res
    return OptResult("UNKNOWN", None, None, None, res.work, f"heuristic tour {length} is above the bound")


def solve_lagrange(inst: Tsp, task: dict, deadline_s: float) -> OptResult:
    started = time.perf_counter()
    heur = nn_two_opt(inst, deadline_s / 2)
    upper = T.verify_tour(inst, heur.witness) or task["bound"] * 2
    pi = optimise_potentials(inst, upper=upper, deadline_s=max(0.1, deadline_s - (time.perf_counter() - started)))
    lb = T.lower_bound(inst, pi)
    if lb is not None and lb > task["bound"]:
        return OptResult("UNSAT", None, "LOWER_BOUND", pi, inst.n, f"1-tree bound {lb} exceeds {task['bound']}")
    return OptResult("UNKNOWN", None, None, None, inst.n, f"1-tree bound {lb} does not exceed {task['bound']}")
