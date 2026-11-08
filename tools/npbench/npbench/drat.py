"""DRAT proof reader and RUP checker.

Scope, stated before the code so it cannot be read as more: this module understands the **DRAT line format**
(comments, ``d`` deletions, literals terminated by ``0``) and checks every added clause by **reverse unit
propagation (RUP)** against the clause database that is active at that line. It does **not** implement RAT
(resolution asymmetric tautology). A clause that is not RUP is reported as ``rat_unsupported`` and the whole
proof keeps the verdict ``unknown`` - the checker never guesses that a RAT step would have been valid.

Why that is the honest boundary: RUP covers the proofs our own CDCL baseline writes and the overwhelming
majority of steps a DRAT-emitting solver produces, but a real DRAT proof may lean on RAT steps. Accepting such
a proof as "DRAT-checked" would be false. The verdict type below therefore has three outcomes and only one of
them is ``unsat``.

Format rules (same spirit as :mod:`npbench.cnf`): ``c`` starts a comment line, ``d`` followed by whitespace starts
a deletion, one ``0`` per line terminates exactly one clause, tokens are ``-?[0-9]{1,9}``, a literal may not
exceed the declared variable count, a blank line is only tolerated after the last clause, and sizes are capped
before anything is built. Nothing is repaired silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .cnf import MAX_BYTES, MAX_CLAUSE_LEN, MAX_DIGITS, Cnf
from .proof import _conflict_after_assuming

# The proof is bounded like the formula is: a checker that allocates first and complains later is a DoS vector.
MAX_PROOF_BYTES = MAX_BYTES
MAX_STEPS = 10_000_000

_LITERAL = re.compile(r"-?[0-9]{1,%d}\Z" % MAX_DIGITS)

UNSAT = "unsat"
UNKNOWN = "unknown"

CHECKED = "checked"
INCOMPLETE_PROOF = "incomplete_proof"
RAT_UNSUPPORTED = "rat_unsupported"
INVALID_STEP = "invalid_step"
MALFORMED = "malformed"


class DratFormatError(ValueError):
    """The input is not acceptable DRAT; nothing was guessed or repaired."""

    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(f"line {line}: {message}" if line else message)


@dataclass(frozen=True)
class DratResult:
    """Outcome of one proof check. Only ``verdict == UNSAT`` means the formula is refuted."""

    verdict: str
    reason: str
    steps: int = 0
    additions: int = 0
    deletions: int = 0
    deletions_not_found: int = 0
    line: int | None = None
    detail: str = ""

    def __bool__(self) -> bool:
        return self.verdict == UNSAT


def parse_drat(text: str, *, num_vars: int | None = None) -> List[Tuple[int, bool, Tuple[int, ...]]]:
    """Parse a DRAT proof into ``(line_number, is_deletion, clause)`` steps.

    Raises :class:`DratFormatError` for anything that is not the strict form above. The empty clause is a real
    step and appears as ``(line, False, ())``.
    """
    if not isinstance(text, str):
        raise DratFormatError(0, "proof input must be text")
    if len(text) > MAX_PROOF_BYTES:
        raise DratFormatError(0, f"proof exceeds {MAX_PROOF_BYTES} bytes")
    lines = text.splitlines()
    last_used = -1
    for index, raw in enumerate(lines):
        if raw.strip():
            last_used = index
    steps: List[Tuple[int, bool, Tuple[int, ...]]] = []
    for index, raw in enumerate(lines):
        number = index + 1
        line = raw.strip()
        if not line:
            if index < last_used:
                raise DratFormatError(number, "blank line inside the proof")
            continue
        if line == "c" or line.startswith(("c ", "c\t")):
            continue
        tokens = line.split()
        deletion = tokens[0] == "d"
        if deletion:
            tokens = tokens[1:]
            if not tokens:
                raise DratFormatError(number, "'d' without a clause")
        if tokens.count("0") > 1 or (tokens.count("0") == 1 and tokens[-1] != "0"):
            raise DratFormatError(number, "exactly one '0' per line, at the end")
        if not tokens or tokens[-1] != "0":
            raise DratFormatError(number, "clause is not terminated by 0")
        clause: List[int] = []
        for token in tokens[:-1]:
            if not _LITERAL.match(token):
                raise DratFormatError(number, f"bad token {token[:20]!r}")
            literal = int(token)
            if literal == 0:
                raise DratFormatError(number, "'0' in the middle of a clause")
            if num_vars is not None and abs(literal) > num_vars:
                raise DratFormatError(number, f"literal {literal} exceeds the declared {num_vars} variables")
            if len(clause) >= MAX_CLAUSE_LEN:
                raise DratFormatError(number, f"clause longer than {MAX_CLAUSE_LEN}")
            clause.append(literal)
        if len(steps) >= MAX_STEPS:
            raise DratFormatError(number, f"more than {MAX_STEPS} steps")
        steps.append((number, deletion, tuple(clause)))
    return steps


class _Database:
    """Active clause multiset with first-match deletion (DRAT deletes by content)."""

    __slots__ = ("_clauses", "_active")

    def __init__(self, clauses: Iterable[Sequence[int]]) -> None:
        self._clauses: List[Tuple[int, ...]] = [tuple(c) for c in clauses]
        self._active: List[bool] = [True] * len(self._clauses)

    def add(self, clause: Sequence[int]) -> None:
        self._clauses.append(tuple(clause))
        self._active.append(True)

    def delete(self, clause: Sequence[int]) -> bool:
        wanted = tuple(clause)
        for index, existing in enumerate(self._clauses):
            if self._active[index] and existing == wanted:
                self._active[index] = False
                return True
        return False

    def active(self) -> List[Tuple[int, ...]]:
        return [c for c, live in zip(self._clauses, self._active) if live]


def check_drat(formula: Cnf, proof: str) -> DratResult:
    """Check a DRAT proof of ``formula`` with RUP per addition; RAT is reported, never assumed."""
    try:
        steps = parse_drat(proof, num_vars=formula.num_vars)
    except DratFormatError as exc:
        return DratResult(verdict=UNKNOWN, reason=MALFORMED, line=exc.line or None, detail=exc.message)
    database = _Database(formula.clauses)
    if any(len(clause) == 0 for clause in formula.clauses):
        return DratResult(verdict=UNSAT, reason=CHECKED, detail="the formula itself contains the empty clause")
    additions = deletions = not_found = 0
    for number, is_deletion, clause in steps:
        if is_deletion:
            deletions += 1
            if not database.delete(clause):
                # DRAT tolerates deleting a clause that is not there; counting it keeps it visible.
                not_found += 1
            continue
        if not _conflict_after_assuming(database.active(), (-literal for literal in clause)):
            reason = INVALID_STEP if not clause else RAT_UNSUPPORTED
            detail = (
                "the empty clause is not RUP; a refutation cannot rest on it"
                if not clause
                else "step is not RUP; RAT is not implemented, so this proof is not accepted"
            )
            return DratResult(
                verdict=UNKNOWN,
                reason=reason,
                steps=number,
                additions=additions,
                deletions=deletions,
                deletions_not_found=not_found,
                line=number,
                detail=detail,
            )
        additions += 1
        if not clause:
            return DratResult(
                verdict=UNSAT,
                reason=CHECKED,
                steps=number,
                additions=additions,
                deletions=deletions,
                deletions_not_found=not_found,
                line=number,
                detail="empty clause accepted by RUP",
            )
        database.add(clause)
    return DratResult(
        verdict=UNKNOWN,
        reason=INCOMPLETE_PROOF,
        steps=len(steps),
        additions=additions,
        deletions=deletions,
        deletions_not_found=not_found,
        detail="the proof ends without the empty clause",
    )
