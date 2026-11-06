#!/usr/bin/env python3
"""Guard for agent/RSI branches: they must not change the files that judge their work (plan P17, docs/superpowers/plans/2026-11-06-freeze-devmode-memory-tiering.md section 4).

Usage: protected_paths.py [--base REF] [--head REF] [--branch NAME] [--json]
  Compares HEAD with the merge base of BASE (default origin/main). The rule applies when the branch name starts with one of the
  configured prefixes (rsi/, agent/); on any other branch the tool only reports and exits 0.
Human override: set HSCL_PROTECTED_OK=1 (a person reviewed the change); the tool then reports and exits 0.
Exit codes: 0 fine or not applicable, 1 protected files changed on a guarded branch, 2 usage/git error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "scripts" / "protected_paths.json"


def compile_pattern(pattern: str) -> re.Pattern:
    """'**' matches across directories, '*' within one path segment, everything else literally."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            if pattern.startswith("/", i):   # '**/' also matches zero directories
                out = out[:-2] + "(?:.*/)?"
                i += 1
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def load_config(path: Path = CONFIG) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data.get("protected"), list) and data["protected"], "protected list missing"
    assert isinstance(data.get("branch_prefixes"), list), "branch_prefixes missing"
    return data


def protected_hits(changed: list[str], patterns: list[str]) -> list[str]:
    rx = [compile_pattern(p) for p in patterns]
    return sorted({c for c in changed if any(r.match(c) for r in rx)})


def guarded_branch(branch: str, prefixes: list[str]) -> bool:
    return any(branch.startswith(p) for p in prefixes)


def git(*args: str, cwd: Path = ROOT) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def changed_files(base: str, head: str, cwd: Path = ROOT) -> list[str]:
    merge_base = git("merge-base", base, head, cwd=cwd)
    out = git("diff", "--name-only", "--no-renames", f"{merge_base}", head, cwd=cwd)
    return [line for line in out.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--branch", help="branch name (default: the current branch)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    try:
        cfg = load_config(repo / "scripts" / "protected_paths.json") if (repo / "scripts" / "protected_paths.json").exists() else load_config()
        branch = args.branch or git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo)
        hits = protected_hits(changed_files(args.base, args.head, cwd=repo), cfg["protected"])
    except (RuntimeError, OSError, ValueError, AssertionError) as e:
        print(f"protected_paths: {e}", file=sys.stderr)
        return 2
    applies = guarded_branch(branch, cfg["branch_prefixes"])
    override = os.environ.get("HSCL_PROTECTED_OK") == "1"
    result = {"branch": branch, "guarded": applies, "override": override, "protected_files_changed": hits}
    if args.json:
        print(json.dumps(result, indent=2))
    elif hits:
        print(f"protected files changed on {branch!r} ({'guarded' if applies else 'not guarded'}):")
        for h in hits:
            print(f"  {h}")
    else:
        print("no protected file changed")
    if hits and applies and not override:
        print("FAIL: an agent/RSI branch must not change the files that judge it; a human sets HSCL_PROTECTED_OK=1 after review", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
