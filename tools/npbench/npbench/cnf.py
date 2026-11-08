"""Strict DIMACS CNF: one reference parser for the benchmark and for later differential tests.

Rules (they answer the parser gaps recorded in docs/research/HCSPNP_BASELINE.md, finding P1):
header ``p cnf <vars> <clauses>`` is required, lowercase, exactly four tokens, before any clause; the parsed
clause count must equal the declared one; tokens are ``-?[0-9]+`` only (no ``+``, no ``_``, no non-ASCII digits); a
literal may not exceed the declared variable count; sizes are capped before anything is built; repeated literals
and tautologies are kept exactly as written (nothing is silently repaired). The SATLIB terminator is accepted only
in its real form: a ``%`` line followed by ``0`` and blank lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Tuple

MAX_VARS = 1_000_000
MAX_CLAUSES = 4_000_000
MAX_CLAUSE_LEN = 1_000_000
MAX_BYTES = 64 * 1024 * 1024
MAX_DIGITS = 9  # a literal or count with more digits cannot be within the caps above

_COUNT = re.compile(r"[0-9]{1,%d}\Z" % MAX_DIGITS)
_LITERAL = re.compile(r"-?[0-9]{1,%d}\Z" % MAX_DIGITS)


class CnfError(ValueError):
    """The input is not acceptable DIMACS CNF; nothing was guessed or repaired."""


@dataclass(frozen=True)
class Cnf:
    num_vars: int
    clauses: Tuple[Tuple[int, ...], ...]


def parse_dimacs(text: str) -> Cnf:
    if not isinstance(text, str):
        raise CnfError("DIMACS input must be text")
    if len(text) > MAX_BYTES or len(text.encode("utf-8", "replace")) > MAX_BYTES:
        raise CnfError(f"input exceeds {MAX_BYTES} bytes")
    num_vars = declared = None
    clauses: list[Tuple[int, ...]] = []
    pending: list[int] = []
    lines = text.splitlines()
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("%"):
            rest = [x.strip() for x in lines[number:]]
            if line != "%" or any(x not in ("", "0") for x in rest) or rest.count("0") > 1:
                raise CnfError(f"line {number}: '%' terminator must be followed only by '0' and blank lines")
            break
        if line.startswith("p"):
            if num_vars is not None:
                raise CnfError(f"line {number}: duplicate header")
            parts = line.split()
            if len(parts) != 4 or parts[0] != "p" or parts[1] != "cnf":
                raise CnfError(f"line {number}: expected exactly 'p cnf <vars> <clauses>'")
            if not _COUNT.match(parts[2]) or not _COUNT.match(parts[3]):
                raise CnfError(f"line {number}: header counts must be digits")
            num_vars, declared = int(parts[2]), int(parts[3])
            if num_vars > MAX_VARS:
                raise CnfError(f"line {number}: {num_vars} variables exceed the cap {MAX_VARS}")
            if declared > MAX_CLAUSES:
                raise CnfError(f"line {number}: {declared} clauses exceed the cap {MAX_CLAUSES}")
            continue
        if num_vars is None:
            raise CnfError(f"line {number}: clause before the header")
        for token in line.split():
            if not _LITERAL.match(token):
                raise CnfError(f"line {number}: bad token {token[:20]!r}")
            lit = int(token)
            if lit == 0:
                if len(clauses) >= declared:
                    raise CnfError(f"line {number}: more clauses than the header declares ({declared})")
                clauses.append(tuple(pending))
                pending = []
                continue
            if abs(lit) > num_vars:
                raise CnfError(f"line {number}: literal {lit} exceeds the declared {num_vars} variables")
            if len(pending) >= MAX_CLAUSE_LEN:
                raise CnfError(f"line {number}: clause longer than {MAX_CLAUSE_LEN}")
            pending.append(lit)
    if num_vars is None:
        raise CnfError("missing header")
    if pending:
        raise CnfError("last clause is not terminated by 0")
    if len(clauses) != declared:
        raise CnfError(f"header declares {declared} clauses, parsed {len(clauses)}")
    return Cnf(num_vars, tuple(clauses))


def write_dimacs(formula: Cnf) -> str:
    out = [f"p cnf {formula.num_vars} {len(formula.clauses)}"]
    out.extend(" ".join(str(x) for x in clause) + (" 0" if clause else "0") for clause in formula.clauses)
    return "\n".join(out) + "\n"


def verify_model(formula: Cnf, model: Mapping[int, bool]) -> bool:
    """True only for a complete model of real booleans that satisfies every clause."""
    for var in range(1, formula.num_vars + 1):
        if not isinstance(model.get(var), bool):
            return False
    return all(any(model[abs(lit)] == (lit > 0) for lit in clause) for clause in formula.clauses)
