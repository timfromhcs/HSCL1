"""Tests for `hscl recovery` CLI subcommands (AGENTS.md section 8.2 & 8.4)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def find_hscl_binary() -> Path | None:
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    newest = max((p.stat().st_mtime for p in (ROOT / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0)
    debug_bin = ROOT / "target" / "debug" / exe
    if debug_bin.is_file() and debug_bin.stat().st_mtime >= newest:
        return debug_bin
    which = shutil.which("hscl")
    if which:
        return Path(which)
    return None


@pytest.fixture
def hscl_bin() -> Path:
    b = find_hscl_binary()
    if b is None:
        pytest.skip("hscl binary not compiled in target/debug")
    return b


def test_recovery_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "recovery", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "readiness:" in res.stdout
    assert "backup directory:" in res.stdout
    assert "snapshots available:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "recovery", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "backup_dir" in data
    assert "backup_dir_exists" in data
    assert "snapshots_found" in data
    assert "timeshift_detected" in data
    assert "snapper_detected" in data
    assert "readiness" in data
    assert "notice" in data


def test_recovery_snapshots_list_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "recovery", "snapshots", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0

    res_j = subprocess.run([str(hscl_bin), "--json", "recovery", "snapshots", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert isinstance(data, list)


def test_recovery_snapshots_create_dry_run(hscl_bin: Path):
    res = subprocess.run(
        [str(hscl_bin), "recovery", "snapshots", "create", "test_baseline", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res.returncode == 0
    assert "[dry-run]" in res.stdout

    res_j = subprocess.run(
        [str(hscl_bin), "--json", "recovery", "snapshots", "create", "test_baseline", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert data["dry_run"] is True
    assert data["executed"] is False
    assert data["label"] == "test_baseline"


def test_recovery_snapshots_create_invalid_label(hscl_bin: Path):
    # Traversal or invalid characters must fail
    res_bad = subprocess.run(
        [str(hscl_bin), "recovery", "snapshots", "create", "../bad_path"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_bad.returncode != 0

    res_spaces = subprocess.run(
        [str(hscl_bin), "recovery", "snapshots", "create", "has spaces in label"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_spaces.returncode != 0


def test_recovery_config_reset_dry_run(hscl_bin: Path):
    res = subprocess.run(
        [str(hscl_bin), "recovery", "config", "reset", "shortcuts", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res.returncode == 0
    assert "[dry-run]" in res.stdout

    res_j = subprocess.run(
        [str(hscl_bin), "--json", "recovery", "config", "reset", "shortcuts", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert data["dry_run"] is True
    assert data["executed"] is False
    assert data["component"] == "shortcuts"
    assert len(data["items"]) >= 1
