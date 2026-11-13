"""Guard for scripts/dev/cleanup-artifacts.ps1, written after it deleted 124 GB by accident.

Root cause, reproduced on 2026-11-13: Windows PowerShell 5.1 returns *every* file for
`Get-ChildItem -LiteralPath <dir> -Recurse -File -Include *.qcow2` (the -Include filter is ignored with
-LiteralPath), while PowerShell 7 honours it. A dry run in the interactive pwsh 7 shell therefore looked correct
and the deletion in 5.1 removed the whole artifacts tree, evidence included.

The gate cannot run PowerShell 5.1 in CI, so it pins the properties that make the mistake impossible:
no -Include, a dry run by default, an explicit protected-extension list, and Where-Object filtering.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev" / "cleanup-artifacts.ps1"


def text() -> str:
    assert SCRIPT.is_file(), "the cleanup script is missing"
    return SCRIPT.read_text(encoding="utf-8")


def code() -> str:
    """The script without its comment lines, so documentation of the bug does not trip the guard."""
    return "\n".join(line for line in text().splitlines() if not line.lstrip().startswith("#"))


def test_it_never_uses_the_include_filter():
    assert "-include" not in code().lower(), (
        "PowerShell 5.1 ignores -Include with -LiteralPath and returns every file; filter with Where-Object"
    )


def test_it_filters_with_where_object_and_an_explicit_disk_extension_list():
    body = text()
    assert "Where-Object" in body
    assert "$diskExt = @('.qcow2', '.raw', '.img')" in body


def test_it_is_a_dry_run_unless_apply_is_passed():
    body = text()
    assert "[switch]$Apply" in body
    assert "if (-not $Apply)" in body
    assert "pass -Apply to delete exactly the files above" in body


def test_it_protects_every_evidence_extension():
    body = text()
    for ext in ("'.json'", "'.png'", "'.md'", "'.log'", "'.txt'", "'.yml'", "'.yaml'", "'.spdx'", "'.html'"):
        assert ext in body, f"{ext} must be protected"


def test_it_keeps_the_newest_iso_and_the_newest_release_set():
    body = text()
    assert "Sort-Object LastWriteTime -Descending" in body
    assert "Select-Object -First 1" in body
    assert "Select-Object -Skip 1" in body
