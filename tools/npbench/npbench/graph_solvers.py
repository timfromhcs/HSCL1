"""Graph solvers and CNF encodings. Every answer is verified by independent code in ``graph_runner``.

* ``coloring_cnf`` / ``ham_cnf``: the encodings. They are part of the problem specification: a bug there would make a
  proof check meaningless, so the tests compare both against brute force on small random graphs.
* ``dsatur``: greedy heuristic, answers SAT or UNKNOWN.
* ``sat_coloring`` / ``sat_ham``: encode, solve with the CDCL baseline, return the model or the RUP proof.
* ``max_clique``: Bron-Kerbosch with pivoting and a deadline; ``complete`` says whether the search finished.
* ``ham_backtrack``: depth-first witness search, answers SAT or UNKNOWN.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .cnf import Cnf
from .graph import Graph
from .solvers import cdcl


@dataclass
class GraphResult:
    status: str  # "SAT" | "UNSAT" | "UNKNOWN"
    witness: Any  # colouring dict, clique list or vertex order
    cert_kind: Optional[str]  # "RUP" | "COLORING_BOUND" | None
    cert: Any
    work: int
    note: str = ""
    complete: bool = False


# ---------------------------------------------------------------------------- encodings
def coloring_cnf(g: Graph, k: int) -> Cnf:
    """Variable (v, c) = (v-1)*k + c + 1. Vertex 1 is fixed to colour 0 (any colouring can be permuted to it)."""
    if k < 1:
        raise ValueError("k must be positive")

    def x(v: int, c: int) -> int:
        return (v - 1) * k + c + 1

    clauses: List[tuple] = [tuple(x(v, c) for c in range(k)) for v in range(1, g.n + 1)]
    for v in range(1, g.n + 1):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append((-x(v, c1), -x(v, c2)))
    for u, v in g.edges:
        for c in range(k):
            clauses.append((-x(u, c), -x(v, c)))
    if g.n >= 1:
        clauses.append((x(1, 0),))
    return Cnf(g.n * k, tuple(clauses))


def decode_coloring(model: Dict[int, bool], g: Graph, k: int) -> Dict[int, int]:
    return {v: next(c for c in range(k) if model[(v - 1) * k + c + 1]) for v in range(1, g.n + 1)}


def ham_cnf(g: Graph) -> Cnf:
    """Variable (v, p) = (v-1)*n + p + 1: vertex v sits at position p of the cycle. Vertex 1 is fixed at position 0."""
    n = g.n
    if n < 3:
        return Cnf(max(n, 1), ((),))  # no Hamiltonian cycle on fewer than 3 vertices: the empty clause

    def x(v: int, p: int) -> int:
        return (v - 1) * n + p + 1

    clauses: List[tuple] = []
    for p in range(n):
        clauses.append(tuple(x(v, p) for v in range(1, n + 1)))
        for v1 in range(1, n + 1):
            for v2 in range(v1 + 1, n + 1):
                clauses.append((-x(v1, p), -x(v2, p)))
    for v in range(1, n + 1):
        clauses.append(tuple(x(v, p) for p in range(n)))
        for p1 in range(n):
            for p2 in range(p1 + 1, n):
                clauses.append((-x(v, p1), -x(v, p2)))
    edge_set = set(g.edges)
    for v1 in range(1, n + 1):
        for v2 in range(1, n + 1):
            if v1 != v2 and ((v1, v2) if v1 < v2 else (v2, v1)) not in edge_set:
                for p in range(n):
                    clauses.append((-x(v1, p), -x(v2, (p + 1) % n)))
    clauses.append((x(1, 0),))
    return Cnf(n * n, tuple(clauses))


def decode_ham(model: Dict[int, bool], g: Graph) -> List[int]:
    n = g.n
    order = [0] * n
    for v in range(1, n + 1):
        for p in range(n):
            if model[(v - 1) * n + p + 1]:
                order[p] = v
    return order


# ------------------------------------------------------------------------------ solvers
def dsatur(g: Graph, k: int, deadline_s: float) -> GraphResult:
    """Greedy DSATUR: SAT with a colouring using at most k colours, otherwise UNKNOWN (a heuristic never says UNSAT)."""
    adj = g.adjacency()
    color: Dict[int, int] = {}
    neighbour_colors: Dict[int, Set[int]] = {v: set() for v in range(1, g.n + 1)}
    for _ in range(g.n):
        v = max((u for u in range(1, g.n + 1) if u not in color), key=lambda u: (len(neighbour_colors[u]), len(adj[u]), -u))
        c = next(c for c in range(g.n + 1) if c not in neighbour_colors[v])
        color[v] = c
        for w in adj[v]:
            neighbour_colors[w].add(c)
    used = max(color.values()) + 1 if color else 0
    if used <= k:
        return GraphResult("SAT", color, None, None, g.n, f"DSATUR used {used} colours")
    return GraphResult("UNKNOWN", None, None, None, g.n, f"DSATUR needed {used} colours, more than {k}")


def sat_coloring(g: Graph, k: int, deadline_s: float) -> GraphResult:
    res = cdcl.solve(coloring_cnf(g, k), deadline_s=deadline_s)
    if res.status == "SAT":
        return GraphResult("SAT", decode_coloring(res.model, g, k), None, None, res.conflicts)
    if res.status == "UNSAT":
        return GraphResult("UNSAT", None, "RUP", res.proof, res.conflicts)
    return GraphResult("UNKNOWN", None, None, None, res.conflicts, res.note)


def sat_ham(g: Graph, deadline_s: float) -> GraphResult:
    res = cdcl.solve(ham_cnf(g), deadline_s=deadline_s)
    if res.status == "SAT":
        return GraphResult("SAT", decode_ham(res.model, g), None, None, res.conflicts)
    if res.status == "UNSAT":
        return GraphResult("UNSAT", None, "RUP", res.proof, res.conflicts)
    return GraphResult("UNKNOWN", None, None, None, res.conflicts, res.note)


def max_clique(g: Graph, deadline_s: float) -> GraphResult:
    """Largest clique found by Bron-Kerbosch with pivoting; ``complete`` is True when the search ran to the end."""
    adj = g.adjacency()
    deadline = time.perf_counter() + float(deadline_s)
    best: List[int] = []
    nodes = 0
    timed_out = False

    def expand(r: List[int], p: Set[int], x: Set[int]) -> None:
        nonlocal best, nodes, timed_out
        if timed_out:
            return
        nodes += 1
        if nodes % 256 == 0 and time.perf_counter() > deadline:
            timed_out = True
            return
        if not p and not x:
            if len(r) > len(best):
                best = list(r)
            return
        if len(r) + len(p) <= len(best):
            return
        pivot = max(p | x, key=lambda u: len(adj[u] & p))
        for v in list(p - adj[pivot]):
            expand(r + [v], p & adj[v], x & adj[v])
            p = p - {v}
            x = x | {v}

    expand([], set(range(1, g.n + 1)), set())
    return GraphResult("SAT" if best else "UNKNOWN", best, None, None, nodes,
                       "search complete" if not timed_out else "deadline reached", complete=not timed_out)


def ham_backtrack(g: Graph, deadline_s: float) -> GraphResult:
    """Depth-first search for a Hamiltonian cycle. Finds a witness or gives up; exhausting the search is not a certificate."""
    n = g.n
    if n < 3:
        return GraphResult("UNKNOWN", None, None, None, 0, "fewer than 3 vertices")
    adj = g.adjacency()
    deadline = time.perf_counter() + float(deadline_s)
    nodes = 0
    path = [1]
    seen = {1}

    def extend() -> Optional[List[int]]:
        nonlocal nodes
        nodes += 1
        if nodes % 512 == 0 and time.perf_counter() > deadline:
            raise TimeoutError
        if len(path) == n:
            return list(path) if path[0] in adj[path[-1]] else None
        candidates = sorted((w for w in adj[path[-1]] if w not in seen), key=lambda w: len(adj[w] - seen))
        for w in candidates:
            path.append(w)
            seen.add(w)
            found = extend()
            if found:
                return found
            path.pop()
            seen.discard(w)
        return None

    try:
        found = extend()
    except TimeoutError:
        return GraphResult("UNKNOWN", None, None, None, nodes, "deadline reached")
    if found:
        return GraphResult("SAT", found, None, None, nodes)
    return GraphResult("UNKNOWN", None, None, None, nodes, "search exhausted without a certificate; not reported as UNSAT")
