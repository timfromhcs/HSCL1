"""Graphs for the benchmark: strict DIMACS ``.col`` reader/writer and verifiers that share no code with any solver.

Strict rules: one ``p edge <n> <m>`` header before any edge, lowercase, digits only (no sign, no underscore, no
non-ASCII digit), vertices in 1..n, no self loops, no repeated edge in either direction, the parsed edge count must equal
the declared one, caps before allocation. Vertices are numbered 1..n; an edge is stored once as ``(u, v)`` with u < v.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Mapping, Sequence, Set, Tuple

MAX_VERTICES = 100_000
MAX_EDGES = 5_000_000
MAX_BYTES = 64 * 1024 * 1024
_COUNT = re.compile(r"[0-9]{1,9}\Z")


class GraphError(ValueError):
    """The input is not acceptable DIMACS .col; nothing was guessed or repaired."""


@dataclass(frozen=True)
class Graph:
    n: int
    edges: Tuple[Tuple[int, int], ...]

    def adjacency(self) -> List[Set[int]]:
        adj: List[Set[int]] = [set() for _ in range(self.n + 1)]
        for u, v in self.edges:
            adj[u].add(v)
            adj[v].add(u)
        return adj


def make_graph(n: int, edge_pairs) -> Graph:
    seen = set()
    for u, v in edge_pairs:
        if u == v or not (1 <= u <= n and 1 <= v <= n):
            raise GraphError(f"bad edge {(u, v)} for n={n}")
        seen.add((u, v) if u < v else (v, u))
    return Graph(n, tuple(sorted(seen)))


def parse_col(text: str) -> Graph:
    if not isinstance(text, str):
        raise GraphError("input must be text")
    if len(text) > MAX_BYTES or len(text.encode("utf-8", "replace")) > MAX_BYTES:
        raise GraphError(f"input exceeds {MAX_BYTES} bytes")
    n = declared = None
    edges: List[Tuple[int, int]] = []
    seen: Set[Tuple[int, int]] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        parts = line.split()
        if parts[0] == "p":
            if n is not None:
                raise GraphError(f"line {number}: duplicate header")
            if len(parts) != 4 or parts[1] != "edge" or not _COUNT.match(parts[2]) or not _COUNT.match(parts[3]):
                raise GraphError(f"line {number}: expected exactly 'p edge <n> <m>' with digit counts")
            n, declared = int(parts[2]), int(parts[3])
            if n > MAX_VERTICES or declared > MAX_EDGES:
                raise GraphError(f"line {number}: size above the cap")
            continue
        if parts[0] == "e":
            if n is None:
                raise GraphError(f"line {number}: edge before the header")
            if len(parts) != 3 or not _COUNT.match(parts[1]) or not _COUNT.match(parts[2]):
                raise GraphError(f"line {number}: expected 'e <u> <v>'")
            u, v = int(parts[1]), int(parts[2])
            if not (1 <= u <= n and 1 <= v <= n) or u == v:
                raise GraphError(f"line {number}: bad edge {u} {v}")
            key = (u, v) if u < v else (v, u)
            if key in seen:
                raise GraphError(f"line {number}: repeated edge {u} {v}")
            if len(edges) >= declared:
                raise GraphError(f"line {number}: more edges than the header declares ({declared})")
            seen.add(key)
            edges.append(key)
            continue
        raise GraphError(f"line {number}: unknown line type {parts[0][:10]!r}")
    if n is None:
        raise GraphError("missing header")
    if len(edges) != declared:
        raise GraphError(f"header declares {declared} edges, parsed {len(edges)}")
    return Graph(n, tuple(sorted(edges)))


def write_col(graph: Graph) -> str:
    return "\n".join([f"p edge {graph.n} {len(graph.edges)}"] + [f"e {u} {v}" for u, v in graph.edges]) + "\n"


def verify_coloring(graph: Graph, colors: Mapping[int, int], k: int) -> bool:
    """Every vertex has an integer colour in 0..k-1 and no edge has equal end colours."""
    for v in range(1, graph.n + 1):
        c = colors.get(v)
        if not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < k:
            return False
    return all(colors[u] != colors[v] for u, v in graph.edges)


def verify_clique(graph: Graph, vertices: Sequence[int], k: int) -> bool:
    """At least ``k`` distinct vertices, pairwise adjacent."""
    vs = list(vertices)
    if len(set(vs)) != len(vs) or len(vs) < k or any(not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= graph.n for v in vs):
        return False
    edge_set = set(graph.edges)
    return all(((a, b) if a < b else (b, a)) in edge_set for i, a in enumerate(vs) for b in vs[i + 1:])


def verify_ham_cycle(graph: Graph, order: Sequence[int]) -> bool:
    """``order`` is a permutation of 1..n (n >= 3) in which consecutive vertices, including the wrap, are adjacent."""
    vs = list(order)
    if graph.n < 3 or len(vs) != graph.n or sorted(vs) != list(range(1, graph.n + 1)):
        return False
    if any(isinstance(v, bool) for v in vs):
        return False
    edge_set = set(graph.edges)
    return all((((a, b) if a < b else (b, a)) in edge_set) for a, b in zip(vs, vs[1:] + vs[:1]))
