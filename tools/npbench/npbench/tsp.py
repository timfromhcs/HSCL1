"""TSP for the benchmark: instance, TSPLIB EUC_2D distances in exact integer arithmetic, verifiers, strict reader.

* ``euc2d``: TSPLIB EUC_2D, the rounded Euclidean distance nint(sqrt(d2)), computed with integers only (no float).
* ``verify_tour``: a permutation of 0..n-1 gives its closed length; anything else gives None.
* ``lower_bound``: the Held-Karp / Lagrangian 1-tree bound for integer potentials ``pi``. For *any* integer vector pi the
  value is a lower bound on the length of every tour (a tour is a 1-tree whose degrees are all 2), so a certificate is just
  the vector and the check is a recomputation here. Vertex 0 is the special vertex.
* ``parse_tsplib``: strict subset (TYPE TSP, EDGE_WEIGHT_TYPE EUC_2D, integer coordinates, ids 1..n in order).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

MAX_BYTES = 16 * 1024 * 1024
MAX_N = 20_000
_INT = re.compile(r"-?[0-9]{1,9}\Z")
_COUNT = re.compile(r"[0-9]{1,9}\Z")


class TspError(ValueError):
    """The input is not acceptable TSPLIB EUC_2D."""


def euc2d(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    d2 = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    r = math.isqrt(d2)
    return r + 1 if d2 - r * r > r else r  # nint(sqrt(d2)): rounds up exactly when d2 > r*r + r


@dataclass(frozen=True)
class Tsp:
    coords: Tuple[Tuple[int, int], ...]

    @property
    def n(self) -> int:
        return len(self.coords)

    def matrix(self) -> List[List[int]]:
        return [[euc2d(a, b) for b in self.coords] for a in self.coords]


def verify_tour(inst: Tsp, order: Sequence[int]) -> Optional[int]:
    if not isinstance(order, (list, tuple)) or len(order) != inst.n:
        return None
    if any(not isinstance(v, int) or isinstance(v, bool) for v in order) or sorted(order) != list(range(inst.n)):
        return None
    return sum(euc2d(inst.coords[order[i]], inst.coords[order[(i + 1) % inst.n]]) for i in range(inst.n))


def lower_bound(inst: Tsp, pi: Sequence[int]) -> Optional[int]:
    n = inst.n
    if n < 3 or not isinstance(pi, (list, tuple)) or len(pi) != n:
        return None
    if any(not isinstance(p, int) or isinstance(p, bool) for p in pi):
        return None
    c = inst.coords

    def w(i: int, j: int) -> int:
        return euc2d(c[i], c[j]) + pi[i] + pi[j]

    # minimum spanning tree on vertices 1..n-1 (Prim), then the two cheapest edges at vertex 0
    in_tree = [False] * n
    best = [None] * n
    best[1] = 0
    total = 0
    for _ in range(n - 1):
        u = min((v for v in range(1, n) if not in_tree[v] and best[v] is not None), key=lambda v: best[v])
        in_tree[u] = True
        total += best[u]
        for v in range(1, n):
            if not in_tree[v]:
                weight = w(u, v)
                if best[v] is None or weight < best[v]:
                    best[v] = weight
    first_two = sorted(w(0, j) for j in range(1, n))[:2]
    return total + sum(first_two) - 2 * sum(pi)


def write_tsplib(inst: Tsp, name: str = "npbench") -> str:
    lines = [f"NAME : {name}", "TYPE : TSP", f"DIMENSION : {inst.n}", "EDGE_WEIGHT_TYPE : EUC_2D", "NODE_COORD_SECTION"]
    lines += [f"{i + 1} {x} {y}" for i, (x, y) in enumerate(inst.coords)]
    return "\n".join(lines + ["EOF"]) + "\n"


def parse_tsplib(text: str) -> Tsp:
    if not isinstance(text, str):
        raise TspError("input must be text")
    if len(text) > MAX_BYTES or len(text.encode("utf-8", "replace")) > MAX_BYTES:
        raise TspError(f"input exceeds {MAX_BYTES} bytes")
    header = {}
    coords: List[Tuple[int, int]] = []
    in_coords = False
    seen_eof = False
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if seen_eof:
            raise TspError(f"line {number}: content after EOF")
        if line == "EOF":
            seen_eof = True
            continue
        if line == "NODE_COORD_SECTION":
            if in_coords or "DIMENSION" not in header:
                raise TspError(f"line {number}: coordinate section before DIMENSION or repeated")
            in_coords = True
            continue
        if not in_coords:
            match = re.match(r"([A-Z_]+)\s*:\s*(.+)\Z", line)
            if not match:
                raise TspError(f"line {number}: expected 'KEY : value'")
            key, value = match.group(1), match.group(2).strip()
            if key in header:
                raise TspError(f"line {number}: repeated key {key}")
            header[key] = value
            continue
        parts = line.split()
        if len(parts) != 3 or not all(_INT.match(p) for p in parts):
            raise TspError(f"line {number}: expected three integers 'id x y'")
        if int(parts[0]) != len(coords) + 1:
            raise TspError(f"line {number}: node ids must be 1..n in order")
        coords.append((int(parts[1]), int(parts[2])))
        if len(coords) > MAX_N:
            raise TspError("too many nodes")
    if header.get("TYPE") != "TSP":
        raise TspError("only TYPE : TSP is supported")
    if header.get("EDGE_WEIGHT_TYPE") != "EUC_2D":
        raise TspError("only EDGE_WEIGHT_TYPE : EUC_2D is supported")
    if "DIMENSION" not in header or not _COUNT.match(header["DIMENSION"]):
        raise TspError("DIMENSION must be digits")
    if not in_coords:
        raise TspError("missing NODE_COORD_SECTION")
    if int(header["DIMENSION"]) != len(coords):
        raise TspError(f"DIMENSION {header['DIMENSION']} but {len(coords)} nodes")
    if len(coords) < 3:
        raise TspError("need at least 3 nodes")
    return Tsp(tuple(coords))
