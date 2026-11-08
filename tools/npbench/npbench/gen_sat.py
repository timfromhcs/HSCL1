"""SAT instance generators with a known answer where one exists.

* ``random_ksat``: the standard uniform model (k distinct variables per clause, each sign with probability 1/2).
* ``threshold_instance``: random 3-SAT at clause/variable ratio 4.26, where the literature puts the hard region
  (the exact peak depends on the solver and the size; see docs/research/NP_BENCHMARK_RESEARCH.md).
* ``planted_ksat``: random k-SAT that a hidden assignment satisfies; answer is SAT by construction.
* ``factoring_cnf``: an array multiplier as CNF. N is fixed in the output bits and both factors must be at least 2,
  so the instance is SAT exactly when N has a factorisation with those bit widths; the expected answer is computed by
  trial division, independent of any solver. A prime N gives a known UNSAT instance.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .cnf import Cnf

GENERATOR_VERSION = "npbench.gen_sat/1"
THRESHOLD_RATIO = 4.26


def random_ksat(n: int, m: int, k: int = 3, *, seed: int) -> Cnf:
    if k < 2:
        raise ValueError("k must be at least 2")
    if n < k:
        raise ValueError("need at least k variables")
    if m < 0:
        raise ValueError("clause count must not be negative")
    rng = random.Random(seed)
    clauses = []
    for _ in range(m):
        variables = rng.sample(range(1, n + 1), k)
        clauses.append(tuple(v if rng.random() < 0.5 else -v for v in variables))
    return Cnf(n, tuple(clauses))


def threshold_instance(n: int, *, seed: int, ratio: float = THRESHOLD_RATIO) -> Cnf:
    return random_ksat(n, round(ratio * n), 3, seed=seed)


def planted_ksat(n: int, m: int, k: int = 3, *, seed: int) -> Tuple[Cnf, Dict[int, bool]]:
    if k < 2 or n < k or m < 0:
        raise ValueError("bad parameters")
    rng = random.Random(seed)
    plant = {v: rng.random() < 0.5 for v in range(1, n + 1)}
    clauses = []
    while len(clauses) < m:
        variables = rng.sample(range(1, n + 1), k)
        clause = tuple(v if rng.random() < 0.5 else -v for v in variables)
        if any(plant[abs(x)] == (x > 0) for x in clause):
            clauses.append(clause)
    return Cnf(n, tuple(clauses)), plant


class _Builder:
    """Tseitin gates over fresh variables."""

    def __init__(self) -> None:
        self.num_vars = 0
        self.clauses: List[Tuple[int, ...]] = []

    def var(self) -> int:
        self.num_vars += 1
        return self.num_vars

    def add(self, *lits: int) -> None:
        self.clauses.append(tuple(lits))

    def and_(self, a: int, b: int) -> int:
        o = self.var()
        self.add(-o, a)
        self.add(-o, b)
        self.add(o, -a, -b)
        return o

    def xor3(self, a: int, b: int, c: int) -> int:
        o = self.var()
        for bits in range(8):
            sa, sb, sc = (bits >> 2) & 1, (bits >> 1) & 1, bits & 1
            # forbid the assignments where o differs from a xor b xor c
            parity = sa ^ sb ^ sc
            self.add(*((-a if sa else a), (-b if sb else b), (-c if sc else c), (o if parity == 1 else -o)))
        return o

    def maj(self, a: int, b: int, c: int) -> int:
        o = self.var()
        self.add(-a, -b, o)
        self.add(-a, -c, o)
        self.add(-b, -c, o)
        self.add(a, b, -o)
        self.add(a, c, -o)
        self.add(b, c, -o)
        return o


def decode_factors(model: Dict[int, bool], bits_p: int, bits_q: int) -> Tuple[int, int]:
    p = sum((1 << i) for i in range(bits_p) if model[1 + i])
    q = sum((1 << j) for j in range(bits_q) if model[1 + bits_p + j])
    return p, q


def factoring_cnf(n: int, *, bits_p: int, bits_q: int) -> Tuple[Cnf, str]:
    """CNF that is satisfiable iff ``n = p * q`` with ``2 <= p < 2**bits_p`` and ``2 <= q < 2**bits_q``."""
    if bits_p < 2 or bits_q < 2:
        raise ValueError("each factor needs at least 2 bits")
    width = bits_p + bits_q
    if n < 0 or n >= (1 << width):
        raise ValueError("n does not fit into the product width")
    b = _Builder()
    a = [b.var() for _ in range(bits_p)]  # variables 1..bits_p are p (little endian)
    c = [b.var() for _ in range(bits_q)]  # next bits_q variables are q
    false = b.var()
    b.add(-false)
    b.add(*a[1:])  # p >= 2: some bit above bit 0 is set
    b.add(*c[1:])  # q >= 2
    acc = [false] * width
    for j in range(bits_q):
        row = [false] * width
        for i in range(bits_p):
            row[i + j] = b.and_(a[i], c[j])
        carry = false
        out = []
        for position in range(width):
            x, y = acc[position], row[position]
            out.append(b.xor3(x, y, carry))
            carry = b.maj(x, y, carry)
        acc = out
    for position in range(width):
        b.add(acc[position] if (n >> position) & 1 else -acc[position])
    truth = any(n % p == 0 and 2 <= n // p < (1 << bits_q) for p in range(2, 1 << bits_p))
    return Cnf(b.num_vars, tuple(b.clauses)), ("SAT" if truth else "UNSAT")
