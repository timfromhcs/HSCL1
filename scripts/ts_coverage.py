#!/usr/bin/env python3
"""Translation coverage report for Qt linguist .ts files (AGENTS.md 10.2: a release gate must fail on missing translations).

Usage: python scripts/ts_coverage.py FILE.ts [FILE.ts ...]
Exit codes: 0 all files complete, 1 at least one problem, 2 usage error or unreadable file.

A message is a problem when its translation is unfinished/vanished/obsolete, empty, or (for non-English files) identical to the source.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BAD_TYPES = {"unfinished", "vanished", "obsolete"}


def check_file(path: Path) -> tuple[str, int, int, list[str]]:
    """Return (language, finished, total, problems) for one .ts file."""
    root = ET.parse(path).getroot()
    lang = root.get("language") or "?"
    english = lang == "en" or lang.startswith("en_")
    total = finished = 0
    problems: list[str] = []
    for message in root.iter("message"):
        total += 1
        source = message.findtext("source") or ""
        tr = message.find("translation")
        text = (tr.text or "") if tr is not None else ""
        kind = tr.get("type") if tr is not None else "unfinished"
        if kind in BAD_TYPES:
            problems.append(f"  unfinished: {source}" if kind == "unfinished" else f"  {kind}: {source}")
        elif not text.strip():
            problems.append(f"  empty: {source}")
        elif not english and text == source:
            problems.append(f"  identical to source: {source}")
        else:
            finished += 1
    return lang, finished, total, problems


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print("usage: ts_coverage.py FILE.ts [FILE.ts ...]", file=sys.stderr)
        return 2
    bad = False
    for p in paths:
        try:
            lang, finished, total, problems = check_file(p)
        except (OSError, ET.ParseError) as e:
            print(f"ts_coverage: {p}: {e}", file=sys.stderr)
            return 2
        print(f"{p.name}: {lang} {finished}/{total} finished")
        for line in problems:
            print(line)
        bad = bad or bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
