"""NP benchmark, slice 5b: differential DIMACS parser test against the CQ-HECS Python parser (audit P1).

Two things are tested, and they are different:

1. **Our** strict parser (`npbench.cnf`) behaves exactly as the matrix says for the seven input classes where the
   CQ-HECS parsers disagree with each other. This half always runs.
2. The **recorded CQ-HECS behaviour** in `docs/research/HCSPNP_BASELINE.md` (finding P1) is still true. This half
   runs the real `cqhecs.sat.parse_dimacs` from the local clone in a separate interpreter (it needs qiskit) and
   compares. It skips with an explicit reason when the clone or that interpreter is not present - a CI runner has
   neither, and a fake differential test would be worse than a skipped one.

The point of the "the classes are still a difference" test: a matrix in which both parsers reject everything would
pass both halves and prove nothing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench.cnf import CnfError, parse_dimacs  # noqa: E402

PROBE = ROOT / "tests" / "helpers" / "cqhecs_parser_probe.py"
CLONE = Path(os.environ.get("HSCL1_CQHECS_CLONE", "/home/tim/src/CQ-HECS"))
CQ_PYTHON = Path(os.path.expanduser(os.environ.get("HSCL1_CQHECS_PYTHON", "~/venvs/cq/bin/python")))


@dataclass(frozen=True)
class Case:
    id: str
    text: str
    ours: str            # "accept" or "reject"
    ours_clauses: tuple | None
    theirs: str          # what cqhecs.sat.parse_dimacs did, measured 2026-11-08 in the clone at 5ed3d2e
    theirs_clauses: tuple | None
    note: str


CASES = (
    Case(
        "baseline", "p cnf 2 1\n1 2 0\n", "accept", ((1, 2),), "accept", ((1, 2),),
        "both parsers agree on a well-formed file; this is the control",
    ),
    Case(
        "a_declared_above_parsed", "p cnf 2 3\n1 2 0\n", "reject", None, "reject", None,
        "header promises 3 clauses, 1 is present. CQ-HECS Python rejects; the native parser accepts "
        "(sat_solver.cpp:138-142 vs 194, the audit's (a))",
    ),
    Case(
        "b_no_header", "1 2 0\n", "reject", None, "reject", None,
        "clause before any p line. CQ-HECS Python rejects; the native parser accepts and grows num_vars "
        "(the audit's (b))",
    ),
    Case(
        "c_satlib_percent", "p cnf 2 1\n1 2 0\n%\n0\n", "accept", ((1, 2),), "accept", ((1, 2),),
        "SATLIB terminator: our parser accepts only the real form (% then 0 and blank lines), the CQ-HECS "
        "Python parser stops at % - the native one rejects it (the audit's (c))",
    ),
    Case(
        "d_underscore_token", "p cnf 2 1\n1_0 2 0\n", "reject", None, "reject", None,
        "1_0: our parser refuses the token. CQ-HECS Python reads int('1_0') = 10 and only rejects because "
        "10 > num_vars - the mechanism differs even where the outcome matches (the audit's (d))",
    ),
    Case(
        "d2_underscore_with_room", "p cnf 10 1\n1_0 0\n", "reject", None, "accept", ((10,),),
        "same token with num_vars=10: CQ-HECS Python accepts the literal 10, our parser still refuses the "
        "token. This is the class where the outcome itself differs",
    ),
    Case(
        "e_upper_cnf", "p CNF 2 1\n1 2 0\n", "reject", None, "accept", ((1, 2),),
        "'p CNF' in capitals: CQ-HECS Python lowercases the line, the native parser requires lowercase, "
        "our parser requires exactly 'p cnf' (the audit's (e))",
    ),
    Case(
        "f_repeated_literal", "p cnf 2 1\n1 1 2 0\n", "accept", ((1, 1, 2),), "accept", ((1, 2),),
        "repeated literal: CQ-HECS Python removes it inside the clause, the native parser keeps it, our "
        "parser keeps it exactly as written - both accept, the clause lists differ (the audit's (f))",
    ),
    Case(
        "g_second_header", "p cnf 2 1\n1 2 0\np cnf 3 1\n1 2 0\n", "reject", None, "reject", None,
        "a second p line after clauses: CQ-HECS Python refuses a duplicate header; the native parser accepts "
        "and overwrites num_vars (the audit's (g))",
    ),
    Case(
        "h_literal_above_num_vars", "p cnf 2 1\n1 9 0\n", "reject", None, "reject", None,
        "literal above the declared variable count: both refuse, different messages",
    ),
    Case(
        "i_unterminated", "p cnf 2 1\n1 2\n", "reject", None, "reject", None,
        "last clause without 0: both refuse",
    ),
)


def ours(text: str) -> tuple[str, tuple | None]:
    try:
        parsed = parse_dimacs(text)
    except CnfError:
        return "reject", None
    return "accept", parsed.clauses


_PROBE_CACHE: dict[str, dict] | None = None


def _run_probe() -> dict[str, dict]:
    """Run the real CQ-HECS parser in its own interpreter; skip (never fake) when it is not there.

    The answer is cached for the session: the interpreter needs qiskit, so it is slow to start and there is no
    reason to pay for it once per parametrized case. A skip inside this function still skips every test that
    asks for it, which is the intent.
    """
    global _PROBE_CACHE
    if _PROBE_CACHE is not None:
        return _PROBE_CACHE
    if not CLONE.is_dir():
        pytest.skip(f"no CQ-HECS clone at {CLONE}; set HSCL1_CQHECS_CLONE to run the differential half")
    if not CQ_PYTHON.is_file():
        pytest.skip(f"no interpreter with qiskit at {CQ_PYTHON}; set HSCL1_CQHECS_PYTHON")
    payload = json.dumps([{"id": case.id, "text": case.text} for case in CASES])
    proc = subprocess.run([str(CQ_PYTHON), str(PROBE)], input=payload, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        pytest.skip(f"probe failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}")
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    if not lines or lines[0].get("probe") != "ok":
        reason = lines[0].get("error") if lines else "no output"
        pytest.skip(f"cqhecs.sat could not be imported in {CQ_PYTHON}: {reason}")
    _PROBE_CACHE = {line["id"]: line for line in lines[1:]}
    return _PROBE_CACHE


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_our_parser_matches_the_matrix(case: Case):
    outcome, clauses = ours(case.text)
    assert outcome == case.ours, f"{case.id}: our parser said {outcome}, the matrix says {case.ours}"
    if case.ours == "accept":
        assert clauses == case.ours_clauses


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_cqhecs_parser_still_behaves_as_recorded(case: Case):
    observed = _run_probe().get(case.id)
    assert observed is not None, f"{case.id}: the probe returned no answer"
    assert observed["outcome"] == case.theirs, (
        f"{case.id}: recorded {case.theirs}, observed {observed['outcome']} "
        f"({observed.get('error', '')}) - the audit row P1 is stale and HCSPNP_BASELINE.md must be corrected"
    )
    if case.theirs == "accept":
        assert tuple(tuple(c) for c in observed["clauses"]) == case.theirs_clauses


def test_the_agreed_classes_are_really_agreed():
    # A matrix where everything differs would also be useless; state the control explicitly.
    agreed = [case.id for case in CASES if case.ours == case.theirs and case.ours == "reject"]
    assert agreed == ["a_declared_above_parsed", "b_no_header", "d_underscore_token", "g_second_header",
                      "h_literal_above_num_vars", "i_unterminated"]


def test_the_differing_classes_are_exactly_the_measured_ones():
    # Measured against the clone at 5ed3d2e; an exact set is stronger than a threshold and fails loudly if a
    # recorded row is edited without a measurement behind it.
    differing = [case.id for case in CASES if (case.ours, case.ours_clauses) != (case.theirs, case.theirs_clauses)]
    assert differing == ["d2_underscore_with_room", "e_upper_cnf", "f_repeated_literal"]
