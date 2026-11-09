"""Unit tests for the hscl dev CLI subcommands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    candidates = [
        root / "target" / "debug" / exe,
        root / "target" / "release" / exe,
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    # Fallback to cargo run if binary not yet compiled
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


def test_dev_status_human_and_json():
    res = _run_hscl(["dev", "status"])
    assert res.returncode == 0, res.stderr
    assert "readiness:" in res.stdout
    assert "git:" in res.stdout
    assert "compilers:" in res.stdout

    res_json = _run_hscl(["dev", "status", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "readiness" in data
    assert "compilers_ready" in data
    assert "git_ready" in data
    assert "python_ready" in data
    assert isinstance(data["installed_tools"], list)


def test_dev_setup_dry_run_and_bundles():
    res = _run_hscl(["dev", "setup", "--dry-run"])
    assert res.returncode == 0, res.stderr
    assert "Dry run:" in res.stdout or "planned" in res.stdout.lower()

    res_json = _run_hscl(["dev", "setup", "python", "--dry-run", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["bundle"] == "python"
    assert data["dry_run"] is True
    assert "python3-venv" in data["packages"]
    assert "apt-get" in data["command"]

    res_bad = _run_hscl(["dev", "setup", "invalid_bundle_name"])
    assert res_bad.returncode != 0
    assert "unknown bundle" in res_bad.stderr.lower()


def test_dev_git_doctor():
    res = _run_hscl(["dev", "git", "doctor"])
    assert res.returncode == 0, res.stderr
    assert "health:" in res.stdout

    res_json = _run_hscl(["dev", "git", "doctor", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "healthy" in data
    assert isinstance(data["issues"], list)
    assert isinstance(data["recommendations"], list)


def test_dev_container_status():
    res = _run_hscl(["dev", "container", "status"])
    assert res.returncode == 0, res.stderr
    assert "podman:" in res.stdout

    res_json = _run_hscl(["dev", "container", "status", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "podman_installed" in data
    assert "rootless_ready" in data
    assert "notice" in data


def test_dev_vm_status():
    res = _run_hscl(["dev", "vm", "status"])
    assert res.returncode == 0, res.stderr
    assert "readiness:" in res.stdout
    assert "guidance:" in res.stdout

    res_json = _run_hscl(["dev", "vm", "status", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "kvm_device_present" in data
    assert "readiness" in data
    assert "guidance" in data
