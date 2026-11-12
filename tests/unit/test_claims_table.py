"""`docs/CLAIMS.md` is the honesty ledger: every row must be a complete, attributable claim.

Two defect classes were found in this file by hand and are pinned here so they cannot come back:

* a row that lost its table shape (an unescaped `|` split the Status cell in two, so the Evidence column
  silently moved one cell to the right - the miner-bridge row had four cells);
* a row with an empty Evidence cell, which turns a claim into an assertion.

Neither can be caught by reading the rendered page, which is why they survived several audits.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIMS = ROOT / "docs/CLAIMS.md"


def _rows():
    text = CLAIMS.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # the header and the |---|---| separator carry no claim
        if set(stripped) <= set("|-: "):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", stripped)[1:-1]]
        yield lineno, cells


def test_every_row_has_exactly_three_cells():
    broken = [(n, len(c), c[0][:60]) for n, c in _rows() if len(c) != 3]
    assert not broken, f"rows must be Feature | Status | Evidence; broken: {broken}"


def test_no_row_claims_without_evidence():
    empty = [c[0][:70] for _, c in _rows() if len(c) == 3 and not c[2]]
    assert not empty, f"a claim without an evidence cell is an assertion: {empty}"


def test_the_ledger_is_not_vacuous():
    rows = list(_rows())
    assert len(rows) > 40, f"only {len(rows)} claim rows parsed - the parser or the file regressed"
