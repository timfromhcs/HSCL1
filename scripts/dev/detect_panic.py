#!/usr/bin/env python3
"""Flag screenshots that look like a kernel panic.

Why: two install runs died with `KERNEL PANIC! Attempted to kill init!` and the only trace was a mostly
uniform purple frame (Ubuntu's panic colour, #772953) among the other screenshots. Reading JSON/console text is
not available from a QMP screenshot, but the colour is distinctive enough to catch it in a batch.

Usage: python scripts/dev/detect_panic.py artifacts/install-luks-final [more dirs...]
Exit: 0 when nothing was flagged, 1 when at least one screenshot looks like a panic (so a loop can react).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

PANIC_RGB = (119, 41, 83)  # Ubuntu #772953
TOLERANCE = 26
SHARE = 0.35  # more than a third of the frame in panic purple


def panic_share(path: Path) -> float:
    with Image.open(path) as im:
        small = im.convert("RGB").resize((160, 100))
    hits = 0
    total = 0
    for y in range(0, 100, 2):
        for x in range(0, 160, 2):
            r, g, b = small.getpixel((x, y))
            total += 1
            if (
                abs(r - PANIC_RGB[0]) <= TOLERANCE
                and abs(g - PANIC_RGB[1]) <= TOLERANCE
                and abs(b - PANIC_RGB[2]) <= TOLERANCE
            ):
                hits += 1
    return hits / total if total else 0.0


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path("artifacts")]
    flagged: list[str] = []
    checked = 0
    for root in roots:
        for png in sorted(root.rglob("*.png")) if root.is_dir() else [root]:
            if png.suffix.lower() != ".png":
                continue
            try:
                share = panic_share(png)
            except Exception as exc:  # a broken PNG must not hide a panic elsewhere
                print(f"skip {png}: {exc}")
                continue
            checked += 1
            if share >= SHARE:
                flagged.append(f"{png} ({share:.0%} panic purple)")
    print(f"checked {checked} screenshot(s)")
    for line in flagged:
        print("PANIC-LIKE:", line)
    if flagged:
        print("Interpret a purple full screen as a crashed guest, not as a UI state.")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
