#!/usr/bin/env python3
"""Enforce the mechanical part of the trademark rules in docs/TRADEMARKS.md (plan Track F/F14, ADR-008).

The legal review is owner work; this script only prevents the rules that *can* be mechanised from regressing:
forbidden wordings, artwork filenames, and a missing attribution sentence in user-facing files.

Exit codes: 0 = clean, 1 = violations found (printed one per line), 2 = could not enumerate the tree.

Usage:
    python scripts/check_trademarks.py            # check the working tree
    python scripts/check_trademarks.py --list     # print the files it inspects
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".md", ".txt", ".rst", ".html", ".htm", ".qml", ".ts", ".json", ".yaml", ".yml", ".toml",
    ".sh", ".py", ".rs", ".desktop", ".svg", ".css", ".js", ".tsx", ".astro", ".conf", ".xml",
}
SKIP_DIRS = {".git", "node_modules", "artifacts", "target", "dist", ".next", "build", "__pycache__", ".pytest_cache"}
SKIP_PATHS = {
    # The rules themselves and the research notes legitimately quote the policy text.
    "docs/TRADEMARKS.md",
    "scripts/check_trademarks.py",
    "tests/unit/test_trademarks.py",
}

# Wordings the policies forbid: a modified mark, a combined mark, or a false equivalence claim.
FORBIDDEN = [
    (re.compile(r"hscl1\s*[- ]?\s*kali", re.I), "HSCL1 and Kali combined into one product name"),
    (re.compile(r"kali\s+edition", re.I), "the mark is modified ('Kali Edition')"),
    (re.compile(r"kali[- ]based\s+hscl1", re.I), "the mark is combined with the product name"),
    (re.compile(r"hscl1\s*[- ]?\s*tails", re.I), "HSCL1 and Tails combined into one product name"),
    (re.compile(r"tails\s+edition", re.I), "the mark is modified ('Tails Edition')"),
    (re.compile(r"hscl1\s+is\s+tails", re.I), "false equivalence with Tails"),
    (re.compile(r"\bis\s+(?:a\s+)?(?:kali|tails)\s+distribution\b", re.I), "false equivalence claim"),
]

# A line that *prohibits* a wording necessarily quotes it. Two ways to say "this is an example, not a use":
#   - the line carries the marker `trademark-ok`, or
#   - the line contains an explicit prohibition cue (reviewed by eye, and the cue is part of the sentence).
EXEMPT_MARKER = "trademark-ok"
PROHIBITION_CUE = re.compile(
    r"\b(never|not|no|forbid\w*|prohibit\w*|avoid|instead of|without|do not|don't|nicht|kein\w*|vermeide\w*|statt)\b",
    re.I,
)

# Artwork we must never bundle (filenames, case-insensitive).
FORBIDDEN_ASSETS = re.compile(r"(kali[-_.]?(logo|dragon|nethunter)|tails[-_.]?logo)", re.I)

KALI = re.compile(r"\bkali\b", re.I)
TAILS = re.compile(r"\btails\b", re.I)
ATTRIBUTION = re.compile(r"trademark of OffSec|Marke von OffSec|marque d'OffSec", re.I)
NON_AFFILIATION = re.compile(
    r"not affiliated with (?:or endorsed by )?the Tails project"
    r"|weder mit dem Tails-Projekt verbunden"
    r"|ni affilié au projet Tails",
    re.I,
)

# The attribution sentence is required on every surface where the product presents itself. A status line such as
# "no Kali repositories configured" is descriptive use; the notice lives on the product surfaces, not in every source file.
ATTRIBUTION_REQUIRED = (
    "README.md",
    "apps/control-center/qml/pages/AboutPage.qml",
    "cli/hscl/src/main.rs",
    "website/content/en.json",
    "website/content/de.json",
    "website/content/fr.json",
)
# Files that talk about privacy/Tails and therefore need the non-affiliation sentence.
PRIVACY_FILES = (
    "README.md",
    "docs/PRIVACY_MODE.md",
    "website/content/en.json",
    "website/content/de.json",
    "website/content/fr.json",
)


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True)
    if out.returncode == 0 and out.stdout:
        rels = [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]
    else:  # not a git checkout (tarball): walk instead of failing
        rels = [str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.rglob("*") if p.is_file()]
    files = []
    for rel in rels:
        rel = rel.replace("\\", "/")
        if rel in SKIP_PATHS:
            continue
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        p = ROOT / rel
        if p.suffix.lower() in TEXT_SUFFIXES and p.is_file():
            files.append(p)
    return sorted(files)


def check(files: list[Path], root: Path | None = None) -> list[str]:
    base = root or ROOT
    problems: list[str] = []
    for p in files:
        rel = p.relative_to(base).as_posix()
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # unreadable file is a real problem, not a silent skip
            problems.append(f"{rel}: cannot read ({exc})")
            continue

        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT_MARKER in line or PROHIBITION_CUE.search(line):
                continue
            for pattern, why in FORBIDDEN:
                m = pattern.search(line)
                if m:
                    problems.append(f"{rel}:{number}: forbidden wording {m.group(0)!r} - {why}")

        if FORBIDDEN_ASSETS.search(p.name):
            problems.append(f"{rel}: filename looks like Kali/Tails artwork")

        if rel in ATTRIBUTION_REQUIRED and KALI.search(text) and not ATTRIBUTION.search(text):
            problems.append(f"{rel}: mentions Kali without 'KALI LINUX (TM) is a trademark of OffSec.'")

        if rel in PRIVACY_FILES and TAILS.search(text) and not NON_AFFILIATION.search(text):
            problems.append(f"{rel}: mentions Tails without the non-affiliation sentence")

    for rel in ATTRIBUTION_REQUIRED:
        if not (base / rel).is_file():
            problems.append(f"{rel}: required trademark surface is missing")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="print the inspected files and exit")
    ap.add_argument("--check", action="store_true", help="default; kept for symmetry with other scripts")
    args = ap.parse_args(argv)

    files = tracked_files()
    if not files:
        print("check_trademarks: no text files found", file=sys.stderr)
        return 2
    if args.list:
        for p in files:
            print(p.relative_to(ROOT).as_posix())
        return 0

    problems = check(files)
    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        print(f"check_trademarks: {len(problems)} problem(s) in {len(files)} files", file=sys.stderr)
        return 1
    print(f"check_trademarks: clean ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
