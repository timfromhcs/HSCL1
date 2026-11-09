"""Website build CLI: unknown flags must not become an output directory, and EN/DE/FR pages must exist.

2026-11-09: `python scripts/build_website.py --help` silently created a directory literally named
`--help` and built 12 pages into it, because the first argument was taken as the output path.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_website.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_unknown_flags_are_rejected_and_create_nothing(tmp_path):
    r = run("--definitely-not-a-flag", cwd=tmp_path)
    assert r.returncode != 0
    assert not (tmp_path / "--definitely-not-a-flag").exists()


def test_help_prints_usage_and_does_not_build_into_a_dash_directory(tmp_path):
    r = run("--help", cwd=tmp_path)
    assert r.returncode == 0
    assert "outdir" in r.stdout
    assert not (tmp_path / "--help").exists()


def test_build_writes_all_three_languages(tmp_path):
    out = tmp_path / "site"
    r = run(str(out))
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").is_file()
    for lang in ("de", "fr"):
        assert (out / lang / "index.html").is_file(), lang
        assert (out / lang / "download" / "index.html").is_file(), lang
