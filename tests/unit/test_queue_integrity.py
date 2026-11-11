"""The queue must stay machine-readable: unique ids, four cells, no recycled numbers.

Written after 2026-11-11: commit c936438 updated "every row starting with `| Q-63 `" instead of
the single ESP row, so the desktop-icon row silently inherited the ESP row's gate and status and
the queue contained Q-63 twice. Two duplicate ids break every `grep '^| Q-63 '` style lookup the
docs and scripts rely on, and the loss only showed up when a human read both rows side by side.
"""

import re
from pathlib import Path

QUEUE = Path(__file__).resolve().parents[2] / "docs" / "AUTONOMOUS_QUEUE.md"

ROW = re.compile(r"^\| (Q-\d+) \|")


def rows() -> list[tuple[int, list[str]]]:
    out = []
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        # `\|` is how a pipe inside a cell has to be written, so it must not split the row
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        out.append((int(m.group(1)[2:]), cells))
    return out


def test_ids_are_unique():
    ids = [n for n, _ in rows()]
    dupes = sorted({n for n in ids if ids.count(n) > 1})
    assert not dupes, f"duplicate queue ids: {dupes}"


def test_ids_are_contiguous_so_a_new_row_cannot_reuse_an_old_one():
    ids = sorted(n for n, _ in rows())
    assert ids == list(range(1, len(ids) + 1)), (
        "queue ids must run 1..N without gaps or reuse, otherwise a new row can silently "
        "inherit an old discussion"
    )


def test_every_row_has_a_gate_and_a_status():
    for n, cells in rows():
        assert len(cells) == 4, f"Q-{n} has {len(cells)} cells, expected 4"
        assert cells[2], f"Q-{n} has an empty gate cell"
        assert cells[3], f"Q-{n} has an empty status cell"


def test_the_two_rows_that_were_merged_are_distinct_again():
    """Regression for the c936438 merge: each row keeps its own subject."""
    by_id = {n: cells for n, cells in rows()}
    icon = by_id[63]
    assert "Desktop icons carry an orange" in icon[1], icon[1]
    assert "untrusted-launcher" in icon[3], "Q-63 lost its own status text"

    esp = next(c for _, c in rows() if "empty ESP" in c[1])
    assert "ESP" in esp[3] and esp[0] != icon[0], "the ESP row must keep its own id and status"
