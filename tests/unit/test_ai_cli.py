"""Unit tests for the hscl ai CLI subcommands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root / "target" / "debug" / "hscl",
        root / "target" / "debug" / "hscl.exe",
        root / "target" / "release" / "hscl",
        root / "target" / "release" / "hscl.exe",
    ]
    for c in candidates:
        if c.is_file():
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
        text=True,
        check=False,
    )


def test_ai_detect_text_and_json():
    res = _run_hscl(["ai", "detect"])
    assert res.returncode == 0, res.stderr
    assert "cpu threads:" in res.stdout.lower()

    res_json = _run_hscl(["ai", "detect", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "cpu_threads" in data
    assert "recommended_backend" in data
    assert "gpu_acceleration_verified" in data
    assert data["gpu_acceleration_verified"] is False


def test_ai_backend_list_and_set():
    res = _run_hscl(["ai", "backend", "list"])
    assert res.returncode == 0, res.stderr
    assert "active backend:" in res.stdout.lower()

    res_json = _run_hscl(["ai", "backend", "list", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert isinstance(data, list)
    names = [b["name"] for b in data]
    assert "auto" in names
    assert "vulkan" in names
    assert "cpu" in names

    # Valid set dry-run
    res_set = _run_hscl(["ai", "backend", "set", "cpu", "--dry-run", "--json"])
    assert res_set.returncode == 0, res_set.stderr
    data_set = json.loads(res_set.stdout)
    assert data_set["backend"] == "cpu"
    assert data_set["dry_run"] is True
    assert data_set["saved"] is False

    # Invalid backend
    res_bad = _run_hscl(["ai", "backend", "set", "quantum_hyperdrive"])
    assert res_bad.returncode != 0
    assert "unknown backend" in res_bad.stderr.lower()


def test_ai_storage_show_and_set():
    res = _run_hscl(["ai", "storage", "show"])
    assert res.returncode == 0, res.stderr
    assert "model storage:" in res.stdout.lower()

    res_json = _run_hscl(["ai", "storage", "show", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "path" in data
    assert "source" in data

    # Valid storage set dry-run
    test_path = "/tmp/hscl_ai_models"
    res_set = _run_hscl(["ai", "storage", "set", test_path, "--dry-run", "--json"])
    assert res_set.returncode == 0, res_set.stderr
    data_set = json.loads(res_set.stdout)
    assert data_set["storage_path"] == test_path
    assert data_set["dry_run"] is True


def test_ai_server_lifecycle_dry_run():
    res_stat = _run_hscl(["ai", "server", "status", "--json"])
    assert res_stat.returncode == 0, res_stat.stderr
    data_stat = json.loads(res_stat.stdout)
    assert "running" in data_stat
    assert data_stat["host"] == "127.0.0.1"
    assert "/v1/models" in data_stat["endpoints"]

    # Start server dry-run
    res_start = _run_hscl(["ai", "server", "start", "--port", "8085", "--dry-run", "--json"])
    assert res_start.returncode == 0, res_start.stderr
    data_start = json.loads(res_start.stdout)
    assert data_start["action"] == "start"
    assert data_start["port"] == 8085
    assert data_start["dry_run"] is True
    assert any("127.0.0.1" in arg for arg in data_start["command"])

    # Stop server dry-run
    res_stop = _run_hscl(["ai", "server", "stop", "--dry-run", "--json"])
    assert res_stop.returncode == 0, res_stop.stderr
    data_stop = json.loads(res_stop.stdout)
    assert data_stop["action"] == "stop"
    assert data_stop["dry_run"] is True


def test_ai_setup_dry_run():
    res = _run_hscl(["ai", "setup", "--backend", "auto", "--dry-run", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["configured_backend"] == "auto"
    assert data["dry_run"] is True
    assert "effective_backend" in data
    assert "storage_dir" in data
