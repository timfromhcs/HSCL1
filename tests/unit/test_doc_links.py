"""Relative Markdown links and images resolve (AGENTS.md 13.3: "Links must be checked").

2026-11-09: the README linked a showcase image whose caption was wrong; the reference itself was valid,
but nothing checked that the target existed at all. This test walks every tracked Markdown file, so a
renamed document or a deleted screenshot is a red gate instead of a 404 on GitHub.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_PREFIX = ("http://", "https://", "mailto:", "#", "data:")


def markdown_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return [ROOT / n.decode("utf-8") for n in out.split(b"\0") if n]


def test_every_relative_markdown_link_resolves():
    broken = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in LINK.findall(text):
            if target.startswith(SKIP_PREFIX):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            if not (path.parent / clean).resolve().exists():
                broken.append((path.relative_to(ROOT).as_posix(), target))
    assert not broken, broken


def test_the_checker_sees_the_documents_it_claims_to_check():
    files = markdown_files()
    assert len(files) > 100, len(files)
    assert any(p.name == "README.md" for p in files)
    assert any(p.name == "KNOWN_LIMITATIONS.md" for p in files)
