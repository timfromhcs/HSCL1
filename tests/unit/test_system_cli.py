"""Unit tests for the hscl system CLI subcommands."""

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


def test_system_info_human_and_json():
    res = _run_hscl(["system", "info"])
    assert res.returncode == 0, res.stderr
    assert len(res.stdout) > 0

    res_json = _run_hscl(["system", "info", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert "os_pretty" in data
    assert "kernel" in data
    assert "arch" in data
    assert "cpu_threads" in data


def test_system_updates_install_dry_run():
    res = _run_hscl(["system", "updates", "--install", "--dry-run"])
    assert res.returncode == 0, res.stderr
    assert "Dry run" in res.stdout or "planned" in res.stdout.lower()

    res_json = _run_hscl(["system", "updates", "--install", "--dry-run", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["action"] == "upgrade"
    assert data["dry_run"] is True
    assert "dist-upgrade" in data["command"]


def test_system_reboot_dry_run():
    res = _run_hscl(["system", "reboot", "--dry-run"])
    assert res.returncode == 0, res.stderr
    assert "Dry run" in res.stdout or "reboot" in res.stdout.lower()

    res_json = _run_hscl(["system", "reboot", "--dry-run", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["action"] == "reboot"
    assert data["dry_run"] is True
    assert data["command"] == ["systemctl", "reboot"]


def test_system_shutdown_dry_run():
    res = _run_hscl(["system", "shutdown", "--dry-run"])
    assert res.returncode == 0, res.stderr
    assert "Dry run" in res.stdout or "shutdown" in res.stdout.lower()

    res_json = _run_hscl(["system", "shutdown", "--dry-run", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert data["action"] == "shutdown"
    assert data["dry_run"] is True
    assert data["command"] == ["systemctl", "poweroff"]


def test_system_services_human_and_json():
    res = _run_hscl(["system", "services", "--enabled"])
    assert res.returncode == 0, res.stderr

    res_json = _run_hscl(["system", "services", "--enabled", "--json"])
    assert res_json.returncode == 0, res_json.stderr
    data = json.loads(res_json.stdout)
    assert isinstance(data, list)
