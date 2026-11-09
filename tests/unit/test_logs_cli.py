"""Tests for `hscl logs` CLI subcommands (AGENTS.md section 8.2, 8.3 & rule 0.3.8)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def find_hscl_binary() -> Path | None:
    debug_bin = ROOT / "target" / "debug" / ("hscl.exe" if os.name == "nt" else "hscl")
    if debug_bin.is_file():
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


def test_logs_show_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "logs", "show"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "=== Log: system" in res.stdout
    assert "redacted" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "logs", "show"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert data["target"] == "system"
    assert data["lines_requested"] == 50
    assert "lines_returned" in data
    assert "content" in data
    assert data["redacted"] is True


def test_logs_show_lines_and_service(hscl_bin: Path):
    res_j = subprocess.run(
        [str(hscl_bin), "--json", "logs", "show", "kernel", "--lines", "15"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert data["target"] == "kernel"
    assert data["lines_requested"] == 15
    assert data["redacted"] is True


def test_logs_collect_stdout_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "logs", "collect"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "=== Diagnostic Log Bundle (redacted," in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "logs", "collect"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "timestamp" in data
    assert data["redacted"] is True
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) >= 2
    for entry in data["entries"]:
        assert "source" in entry
        assert "lines" in entry
        assert "bytes" in entry
        assert "content" in entry


def test_logs_collect_output_file_and_refuses_overwrite(hscl_bin: Path, tmp_path: Path):
    bundle_file = tmp_path / "diag_bundle.json"
    assert not bundle_file.exists()

    res = subprocess.run(
        [str(hscl_bin), "logs", "collect", "--output", str(bundle_file)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res.returncode == 0
    assert "Collected" in res.stdout
    assert bundle_file.is_file()

    with open(bundle_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["redacted"] is True
    assert len(data["entries"]) >= 2

    # Second run must refuse overwrite
    res_refuse = subprocess.run(
        [str(hscl_bin), "logs", "collect", "--output", str(bundle_file)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res_refuse.returncode != 0
    assert "refusing to overwrite" in res_refuse.stderr
