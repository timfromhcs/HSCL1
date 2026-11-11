"""The publish helper must upload the parts first, one call each, and publish explicitly.

Written after 2026-11-11: a single `gh release create` with every asset stalled twice on a 1.9 GB part,
leaving a *draft* release with an `untagged-...` URL while its small assets were already visible. These
tests exercise the dry-run plan, so no network and no release is touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_publish.py"


def make_set(tmp_path: Path) -> Path:
    d = tmp_path / "set"
    d.mkdir()
    for name in (
        "HSCL1-1.2.3-alpha.0-amd64.iso.part000",
        "HSCL1-1.2.3-alpha.0-amd64.iso.part001",
        "SHA256SUMS",
        "release-notes.md",
        "SBOM-hscl-cli.spdx.json",
        "build-manifest.json",
        "HSCL1-1.2.3-alpha.0-amd64.iso.manifest.json",
    ):
        (d / name).write_text("x", encoding="utf-8")
    return d


def plan(tmp_path: Path, *extra: str) -> list[str]:
    d = make_set(tmp_path)
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--version", "1.2.3-alpha.0", "--release-dir", str(d),
         "--dry-run", "--skip-verify", *extra],
        capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, res.stderr
    return [l for l in res.stdout.splitlines() if l.startswith("[dry-run]")]


def test_parts_are_uploaded_first_and_one_call_each(tmp_path):
    steps = plan(tmp_path)
    uploads = [s for s in steps if "release upload" in s]
    assert uploads, steps
    assert "part000" in uploads[0] and "part001" in uploads[1], uploads
    assert len(uploads) == 7, uploads
    assert all("--clobber" in s for s in uploads), "re-runs after a stall must be able to replace an asset"


def test_the_release_is_created_as_a_draft_and_published_explicitly(tmp_path):
    steps = plan(tmp_path)
    assert "create" in steps[0] and "--draft" in steps[0], steps[0]
    assert steps[-1].endswith("--draft=false --prerelease"), steps[-1]


def test_draft_only_stops_before_publishing(tmp_path):
    steps = plan(tmp_path, "--draft-only")
    assert not any("--draft=false" in s for s in steps), steps
