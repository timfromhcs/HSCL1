"""Handbook checks: identical chapter tree in en/de/fr, valid links, documented hscl commands exist."""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HB = ROOT / "handbook"
LANGS = ["en", "de", "fr"]


def chapters(lang):
    return sorted(p.name for p in (HB / lang / "src").glob("*.md"))


def test_same_chapter_tree_in_all_languages():
    assert chapters("en") == chapters("de") == chapters("fr")
    assert len(chapters("en")) >= 10


@pytest.mark.parametrize("lang", LANGS)
def test_summary_links_and_internal_links_resolve(lang):
    src = HB / lang / "src"
    summary = (src / "SUMMARY.md").read_text(encoding="utf-8")
    linked = re.findall(r"\]\(([^)#]+\.md)\)", summary)
    assert sorted(linked) == sorted(p for p in chapters(lang) if p != "SUMMARY.md")
    for md in src.glob("*.md"):
        for target in re.findall(r"\]\(([^):#]+\.md)(?:#[^)]*)?\)", md.read_text(encoding="utf-8")):
            assert (src / target).exists(), f"{lang}/{md.name} links to missing {target}"


@pytest.mark.parametrize("lang", LANGS)
def test_product_name_and_honest_status(lang):
    text = (HB / lang / "src" / "introduction.md").read_text(encoding="utf-8")
    assert "HSCL1" in text and "hcsmedia" in text
    assert "Tails" in text and "Kali" in text
    for forbidden in ("HSCL ", "HCSL1", "100% secure", "anonymous OS"):
        assert forbidden not in text


def documented_commands():
    seen = set()
    for lang in LANGS:
        for md in (HB / lang / "src").glob("*.md"):
            for block in re.findall(r"```console\n(.*?)```", md.read_text(encoding="utf-8"), re.S):
                for line in block.splitlines():
                    m = re.match(r"\$ hscl (.+)", line)
                    if m:
                        words = []
                        for w in m.group(1).split():
                            if w.startswith("-"):
                                break
                            words.append(w)
                        seen.add(tuple(words))
    return sorted(seen)


@pytest.mark.parametrize("words", documented_commands())
def test_documented_hscl_commands_exist(words):
    r = subprocess.run(["cargo", "run", "-q", "-p", "hscl", "--", *words, "--help"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (words, r.stderr[-300:])
