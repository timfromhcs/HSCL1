"""Unit tests for the hscl appearance CLI subcommands."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    newest = max((p.stat().st_mtime for p in (root / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0)
    candidates = [
        root / "target" / "debug" / exe,
        root / "target" / "release" / exe,
    ]
    for c in candidates:
        if c.is_file() and c.stat().st_mtime >= newest:
            return str(c)
    return "cargo"


def _run_hscl(args: list[str]) -> subprocess.CompletedProcess[str]:
    bin_path = _find_hscl()
    if bin_path == "cargo":
        cmd = ["cargo", "run", "-q", "-p", "hscl", "--"] + args
    else:
        cmd = [bin_path] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        check=False,
    )


def test_appearance_mode_show_and_set_dry_run():
    res = _run_hscl(["appearance", "mode"])
    assert res.returncode == 0, res.stderr
    assert "mode:" in res.stdout.lower()

    res_json = _run_hscl(["appearance", "mode", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "mode" in data

    res_set = _run_hscl(["appearance", "mode", "light", "--dry-run"])
    assert res_set.returncode == 0, res_set.stderr
    assert "dry run" in res_set.stdout.lower()

    res_set_json = _run_hscl(["appearance", "mode", "dark", "--dry-run", "--json"])
    assert res_set_json.returncode == 0, res_set_json.stderr
    data_set = json.loads(res_set_json.stdout)
    assert data_set["mode"] == "dark"
    assert data_set["dry_run"] is True

    res_bad = _run_hscl(["appearance", "mode", "neon_rainbow"])
    assert res_bad.returncode != 0
    assert "invalid appearance mode" in res_bad.stderr.lower()


def test_appearance_dock_position():
    res = _run_hscl(["appearance", "dock", "position", "bottom", "--dry-run"])
    assert res.returncode == 0, res.stderr
    assert "dry run" in res.stdout.lower()

    res_json = _run_hscl(["appearance", "dock", "position", "left", "--dry-run", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["position"] == "left"
    assert data["dry_run"] is True

    res_bad = _run_hscl(["appearance", "dock", "position", "diagonal"])
    assert res_bad.returncode != 0
    assert "invalid dock position" in res_bad.stderr.lower()


def test_appearance_wallpaper_list():
    res = _run_hscl(["appearance", "wallpaper", "list"])
    assert res.returncode == 0, res.stderr
    assert "wallpaper" in res.stdout.lower()

    res_json = _run_hscl(["appearance", "wallpaper", "list", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert isinstance(data, list)
