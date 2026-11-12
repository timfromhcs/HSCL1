"""Bump the release version in the seven files the release commit touches (same set as 13c3215)."""
import re
import sys
from pathlib import Path

OLD = Path("VERSION").read_text(encoding="utf-8").strip()
NEW = sys.argv[1] if len(sys.argv) > 1 else "0.1.7-alpha.0"
if OLD == NEW:
    raise SystemExit(f"VERSION is already {NEW}")

TARGETS = [
    "VERSION",
    "Cargo.toml",
    "Cargo.lock",
    "packages/debian/hscl-branding/etc/calamares/branding/hscl1/branding.desc",
    "handbook/en/src/introduction.md",
    "handbook/de/src/introduction.md",
    "handbook/fr/src/introduction.md",
]

for name in TARGETS:
    p = Path(name)
    text = p.read_text(encoding="utf-8")
    if OLD not in text:
        print(f"SKIP {name}: no {OLD}")
        continue
    n = text.count(OLD)
    p.write_text(text.replace(OLD, NEW), encoding="utf-8", newline="\n")
    print(f"{name}: {n} replaced")

# VERSION has no trailing newline in this repo; keep whatever it had.
v = Path("VERSION").read_bytes()
print("VERSION bytes:", v)
