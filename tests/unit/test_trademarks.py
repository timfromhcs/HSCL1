"""scripts/check_trademarks.py: the mechanical trademark rules must be enforced, not just documented (ADR-008)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_trademarks as ct  # noqa: E402

NOTICE = "KALI LINUX™ is a trademark of OffSec."
TAILS = "HSCL1 is not affiliated with or endorsed by the Tails project."


def tree(tmp_path, files):
    """Create a fake repository root; every path in `files` is written, parents included."""
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def surfaces(**overrides):
    """The minimum set the checker requires to exist."""
    base = {rel: "nothing here" for rel in ct.ATTRIBUTION_REQUIRED}
    base.update(overrides)
    return base


def problems_for(tmp_path, files):
    root = tree(tmp_path, files)
    return ct.check(sorted(p for p in root.rglob("*") if p.is_file()), root=root)


def test_a_complete_clean_tree_passes(tmp_path):
    assert problems_for(tmp_path, surfaces()) == []


def test_missing_required_surface_is_reported(tmp_path):
    files = surfaces()
    del files["README.md"]
    assert any("required trademark surface is missing" in p for p in problems_for(tmp_path, files))


def test_a_forbidden_combined_name_is_reported(tmp_path):
    out = problems_for(tmp_path, surfaces(**{"docs/POLICY.md": '{"t": "HSCL1 Kali Edition"}'}))
    assert any("forbidden wording" in p for p in out)


def test_a_line_that_prohibits_the_wording_is_exempt(tmp_path):
    text = 'Never write "HSCL1 Kali Edition" on the website.'
    assert problems_for(tmp_path, surfaces(**{"docs/POLICY.md": text})) == []


def test_explicit_marker_exempts_a_quoted_example(tmp_path):
    text = 'the pattern "HSCL1 Kali Edition" is forbidden. <!-- trademark-ok -->'
    assert problems_for(tmp_path, surfaces(**{"docs/POLICY.md": text})) == []


def test_artwork_filename_is_reported(tmp_path):
    out = problems_for(tmp_path, surfaces(**{"themes/hcs-default/kali-dragon.svg": "<svg/>"}))
    assert any("artwork" in p for p in out)


def test_attribution_missing_on_a_surface_that_mentions_the_mark(tmp_path):
    out = problems_for(tmp_path, surfaces(**{"README.md": "Kali tools run in containers."}))
    assert any("without 'KALI LINUX" in p for p in out)


def test_attribution_present_in_english_works(tmp_path):
    assert problems_for(tmp_path, surfaces(**{"README.md": f"Kali tools. {NOTICE} {TAILS}"})) == []


def test_attribution_present_in_german_and_french_works(tmp_path):
    de = "Kali-Werkzeuge. KALI LINUX™ ist eine Marke von OffSec. HSCL1 ist weder mit dem Tails-Projekt verbunden noch von ihm unterstützt."
    fr = "Outils Kali. KALI LINUX™ est une marque d'OffSec. HSCL1 n'est ni affilié au projet Tails ni approuvé par lui."
    out = problems_for(tmp_path, surfaces(**{"website/content/de.json": de, "website/content/fr.json": fr}))
    assert out == []


def test_tails_mention_without_non_affiliation_sentence(tmp_path):
    out = problems_for(tmp_path, surfaces(**{"README.md": "We launch the official Tails ISO."}))
    assert any("non-affiliation" in p for p in out)


def test_status_lines_may_mention_the_mark_without_a_notice(tmp_path):
    """A CLI status message is descriptive use; the notice lives on the product surfaces."""
    out = problems_for(tmp_path, surfaces(**{"cli/hscl/src/security.rs": 'print("no Kali repositories configured")'}))
    assert out == []


def test_the_real_repository_is_clean():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/check_trademarks.py")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_binary_and_build_directories_are_skipped():
    rels = [p.relative_to(ROOT).as_posix() for p in ct.tracked_files()]
    assert rels, "tracked_files() returned nothing"
    assert not any("/artifacts/" in "/" + r or r.startswith("artifacts/") for r in rels)
    assert not any(r.startswith(".git/") for r in rels)
