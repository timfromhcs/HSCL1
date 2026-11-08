"""Tests for `hscl privacy` CLI subcommands (AGENTS.md section 6.5 & 8.2)."""
from __future__ import annotations

import hashlib
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


def test_privacy_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "privacy", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "ephemeral overlay:" in res.stdout
    assert "root filesystem:" in res.stdout
    assert "zram memory swap:" in res.stdout
    assert "core dumps:" in res.stdout
    assert "tor service:" in res.stdout
    assert "tor browser:" in res.stdout
    assert "Notice: HSCL1 Privacy Mode is NOT Tails" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "ephemeral_overlay" in data
    assert "root_fstype" in data
    assert "persistent_swap_active" in data
    assert "zram_swap_active" in data
    assert "suid_dumpable_disabled" in data
    assert "internal_disks_automounted" in data
    assert "tor_service_active" in data
    assert "tor_browser_installed" in data
    assert "disclaimer" in data
    assert "NOT Tails" in data["disclaimer"]
    assert "no claim of absolute anonymity" in data["disclaimer"]


def test_privacy_tor_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "privacy", "tor", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "tor service:" in res.stdout
    assert "tor browser:" in res.stdout
    assert "fail-closed:    enforced (no direct browser fallback)" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "tor", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "service_active" in data
    assert "browser_installed" in data
    assert data["fail_closed_policy"] is True
    assert "notice" in data


def test_privacy_tor_launch_fail_closed_without_browser(hscl_bin: Path):
    # In test environments without torbrowser-launcher, must fail closed
    res = subprocess.run([str(hscl_bin), "privacy", "tor", "launch", "--dry-run"], capture_output=True, text=True, cwd=str(ROOT))
    if shutil.which("torbrowser-launcher") is None and shutil.which("tor-browser") is None:
        assert res.returncode != 0
        output = res.stdout + res.stderr
        assert "fail-closed" in output
        assert "prohibited" in output
    else:
        assert res.returncode == 0
        assert "[dry-run]" in res.stdout


def test_privacy_session_explain_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "privacy", "session", "explain"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "Ephemeral Overlay Filesystem" in res.stdout
    assert "Volatile Memory & Swap Security" in res.stdout
    assert "fs.suid_dumpable = 0" in res.stdout
    assert "Host Storage Isolation" in res.stdout
    assert "Tor Network & Browser Fail-Closed Policy" in res.stdout
    assert "Clear Boundaries vs Authentic Tails" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "session", "explain"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "explanation" in data
    assert "disclaimer" in data
    assert "NOT Tails" in data["disclaimer"]


def test_privacy_tails_verify_and_launch(hscl_bin: Path, tmp_path: Path):
    dummy_iso = tmp_path / "tails-amd64-test.iso"
    # Write 101MB dummy data so it meets minimum ISO size requirement (100MB)
    chunk = b"X" * (1024 * 1024)  # exactly 1 MB
    h = hashlib.sha256()
    with open(dummy_iso, "wb") as f:
        for _ in range(101):
            f.write(chunk)
            h.update(chunk)
    valid_sha = h.hexdigest()

    # 1. Verify without expected sha (calculates hash)
    res = subprocess.run([str(hscl_bin), "--json", "privacy", "tails", "verify", str(dummy_iso)], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["verified"] is True
    assert data["calculated_sha256"] == valid_sha
    assert data["size_bytes"] == dummy_iso.stat().st_size
    assert "tails.net" in data["tails_doc_url"]

    # 2. Verify with matching expected sha
    res_match = subprocess.run(
        [str(hscl_bin), "--json", "privacy", "tails", "verify", str(dummy_iso), "--expected-sha256", valid_sha],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res_match.returncode == 0
    data_match = json.loads(res_match.stdout)
    assert data_match["verified"] is True
    assert data_match["expected_sha256"] == valid_sha

    # 3. Verify with mismatched expected sha must fail
    res_mismatch = subprocess.run(
        [str(hscl_bin), "privacy", "tails", "verify", str(dummy_iso), "--expected-sha256", "0" * 64],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res_mismatch.returncode != 0
    assert "checksum mismatch" in (res_mismatch.stdout + res_mismatch.stderr).lower()

    # 4. Tails Launch --dry-run builds isolated QEMU command
    res_launch = subprocess.run(
        [str(hscl_bin), "--json", "privacy", "tails", "launch", str(dummy_iso), "--ram-mb", "8192", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res_launch.returncode == 0
    data_launch = json.loads(res_launch.stdout)
    assert data_launch["dry_run"] is True
    assert data_launch["ram_mb"] == 8192
    assert "qemu-system-x86_64" in data_launch["command"]
    assert "-m 8192" in data_launch["command"]
    assert "-snapshot" in data_launch["command"]
    assert str(dummy_iso) in data_launch["command"]
    assert "-hda" not in data_launch["command"]  # isolated, no host storage
