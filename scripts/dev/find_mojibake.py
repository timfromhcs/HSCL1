"""Scan tracked text files for U+FFFD replacement characters (mojibake damage)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAD = "\ufffd"
TEXT_EXT = {
    ".md", ".ts", ".tsx", ".qml", ".json", ".py", ".rs", ".sh", ".txt", ".html",
    ".js", ".jsx", ".yml", ".yaml", ".toml", ".desktop", ".menu", ".directory",
    ".css", ".svg", ".xml", ".ini", ".conf", ".service", ".rules", ".plymouth",
    ".category", ".gitignore", ".env.example", ".spec",
}


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    for name in out.split("\0"):
        if name:
            yield ROOT / name


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    rows = []
    for path in tracked_files():
        if only and only not in path.as_posix():
            continue
        if path.suffix.lower() not in TEXT_EXT and path.name not in TEXT_EXT:
            continue
        try:
            if path.stat().st_size > 4_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        n = text.count(BAD)
        if n:
            rows.append((n, path.relative_to(ROOT).as_posix()))
    rows.sort(reverse=True)
    for n, name in rows:
        print(f"{n:5d}  {name}")
    print(f"total files: {len(rows)}  total chars: {sum(n for n, _ in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
