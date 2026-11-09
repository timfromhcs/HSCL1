"""Check relative Markdown links and image references across the repository."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_PREFIX = ("http://", "https://", "mailto:", "#", "data:")


def markdown_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / n.decode("utf-8") for n in out.split(b"\0") if n]


def main() -> int:
    broken = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in LINK.findall(text):
            if target.startswith(SKIP_PREFIX):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            dest = (path.parent / clean).resolve()
            if not dest.exists():
                broken.append((path.relative_to(ROOT).as_posix(), target))
    for src, target in broken:
        print(f"{src} -> {target}")
    print(f"broken: {len(broken)} / files: {len(markdown_files())}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
