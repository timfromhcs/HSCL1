#!/usr/bin/env python3
"""Gate against unbacked update claims (plan F1).

HSCL1 updates with APT on top of Ubuntu; the archive has no `grub-btrfs`, so booting into a snapshot does not exist, and nothing in
the system is immutable. User-facing text (README, docs, handbook, website) must therefore not say "atomic", "immutable" (also the
German and French forms) or "boot into a snapshot" unless the same clause negates it ("not atomic", "kein", "pas", "never", ...).
Research notes and plans (docs/research, docs/superpowers) discuss these ideas and are not scanned.

Usage: python scripts/check_update_claims.py [--root DIR]        Exit codes: 0 = clean, 1 = claims found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CLAIMS = (
    re.compile(r"\b(?:atomic|atomar\w*|atomique\w*)\b", re.I),
    re.compile(r"\b(?:immutable|unveränderlich\w*|immuable\w*)\b", re.I),
    re.compile(r"\bboot(?:s|ing)?\s+(?:in)?to\s+(?:a\s+)?snapshots?\b", re.I),
)
NEGATION = re.compile(r"\b(?:not|no|nor|neither|never|without|nicht|kein\w*|nie|niemals|ne|pas|jamais|aucun\w*)\b|n't\b", re.I)
CLAUSE_SPLIT = re.compile(r"[.;:!?,()–—]")
TEXT_SUFFIXES = {".md", ".mdx", ".txt", ".json", ".html", ".astro", ".ts", ".tsx", ".vue", ".qml", ".toml"}
SKIP_PARTS = {"node_modules", "dist", ".astro", ".vercel", ".git", "target", "artifacts", "__pycache__"}
SKIP_PREFIXES = ("docs/research/", "docs/superpowers/")
ROOTS = ("README.md", "docs", "handbook", "website")


def _files(root: Path):
    for entry in ROOTS:
        base = root / entry
        if base.is_file():
            yield base
        elif base.is_dir():
            for p in sorted(base.rglob("*")):
                rel = p.relative_to(root).as_posix()
                if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and not (SKIP_PARTS & set(p.relative_to(root).parts)) and not rel.startswith(SKIP_PREFIXES):
                    yield p


def _clause(line: str, start: int, end: int) -> str:
    lo = max((m.end() for m in CLAUSE_SPLIT.finditer(line, 0, start)), default=0)
    nxt = CLAUSE_SPLIT.search(line, end)
    return line[lo : nxt.start() if nxt else len(line)]


def check(root: Path) -> list[str]:
    root = Path(root)
    errs: list[str] = []
    for p in _files(root):
        rel = p.relative_to(root).as_posix()
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            for pat in CLAIMS:
                for m in pat.finditer(line):
                    if not NEGATION.search(_clause(line, m.start(), m.end())):
                        errs.append(f"{rel}:{n}: unbacked update claim '{m.group(0).lower()}' - say what is true or negate it explicitly")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    a = ap.parse_args(argv)
    errs = check(a.root)
    for e in errs:
        print(e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
