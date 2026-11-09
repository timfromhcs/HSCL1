"""Showcase evidence: every README image exists, the manifest lists exactly the shipped images,
and no evidence image is referenced without being listed.

Visual QA 2026-11-09: `13_offline_handbook.png` was captioned "Trilingual Offline Handbook" but
contained only the desktop. The file is gone; this test keeps the reference set and the manifest in
step so a dangling or unlisted image is a red gate instead of a silent broken caption.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOWCASE = ROOT / "docs" / "img" / "showcase"
README = (ROOT / "README.md").read_text(encoding="utf-8")


def manifest() -> dict[str, dict]:
    entries = json.loads((SHOWCASE / "manifest.json").read_text(encoding="utf-8"))
    return {e["filename"]: e for e in entries}


def test_every_showcase_image_is_listed_in_the_manifest():
    shipped = {p.name for p in SHOWCASE.glob("*.png")}
    listed = set(manifest())
    assert shipped == listed, {
        "unlisted": sorted(shipped - listed),
        "missing": sorted(listed - shipped),
    }


def test_every_image_linked_from_the_readme_exists():
    links = set(re.findall(r"\]\((docs/img/[^)\s]+\.png)\)", README))
    assert len(links) >= 8, links
    missing = [link for link in links if not (ROOT / link).is_file()]
    assert not missing, missing


def test_the_manifest_records_a_description_for_every_image():
    for name, entry in manifest().items():
        assert entry.get("description"), name
        assert entry.get("size") == [1280, 800] or entry.get("size"), name


def test_no_evidence_image_claims_an_app_that_is_not_in_the_picture():
    """The handbook capture really shows the handbook now (Firefox on /usr/share/doc/hscl-handbook).
    It must only be re-added together with a manifest entry, which the consistency test enforces;
    the previous false capture was a bare desktop."""
    path = SHOWCASE / "13_offline_handbook.png"
    if path.exists():
        assert "13_offline_handbook.png" in manifest(), "re-added without a manifest entry"
        assert manifest()["13_offline_handbook.png"].get("source_iso"), "evidence needs its artifact"
