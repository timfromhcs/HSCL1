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


def test_privacy_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "privacy", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "session:" in res.stdout
    assert "ephemeral overlay:" in res.stdout
    assert "root filesystem:" in res.stdout
    assert "zram memory swap:" in res.stdout
    assert "core dumps:" in res.stdout
    assert "tor service:" in res.stdout
    assert "tor browser:" in res.stdout
    assert "Notice: HSCL1 Privacy Mode is NOT Tails" in res.stdout


def test_privacy_status_does_not_warn_about_normal_swap_outside_a_privacy_session(hscl_bin: Path):
    """Measured 2026-11-10 in the installed VM: the installer's own swap file was reported as a WARNING.

    A persistent disk swap is only a problem in a session that claims to be ephemeral, so the wording must
    depend on the session type instead of warning unconditionally.
    """
    res = subprocess.run([str(hscl_bin), "privacy", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    if "ephemeral (volatile RAM overlay)" in res.stdout:
        assert "WARNING: active persistent disk swap" in res.stdout or "none" in res.stdout
    else:
        assert "installed (persistent root)" in res.stdout
        assert "WARNING: active persistent disk swap" not in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
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
    res = subprocess.run([str(hscl_bin), "privacy", "tor", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "tor service:" in res.stdout
    assert "tor browser:" in res.stdout
    assert "tor launch:     requires Tor Browser (no substitute; egress is NOT filtered)" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "tor", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "service_active" in data
    assert "browser_installed" in data
    assert data["tor_launch_requires_browser"] is True
    assert "fail_closed_policy" not in data, "the old field claimed a network policy that does not exist"
    assert "notice" in data


def test_privacy_tor_launch_refuses_without_a_browser(hscl_bin: Path):
    # Without torbrowser-launcher the launcher must refuse, and must not pretend to filter egress
    res = subprocess.run([str(hscl_bin), "privacy", "tor", "launch", "--dry-run"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    if shutil.which("torbrowser-launcher") is None and shutil.which("tor-browser") is None:
        assert res.returncode != 0
        output = res.stdout + res.stderr
        assert "refuses to start a different browser" in output
        assert "does not block direct browsing" in output
    else:
        assert res.returncode == 0
        assert "[dry-run]" in res.stdout


def test_privacy_session_explain_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "privacy", "session", "explain"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "Ephemeral Overlay Filesystem" in res.stdout
    assert "Volatile Memory & Swap Security" in res.stdout
    assert "fs.suid_dumpable = 0" in res.stdout
    assert "Host Storage Isolation" in res.stdout
    assert "Tor Launcher, and What Is NOT Enforced" in res.stdout
    assert "does NOT filter egress" in res.stdout
    assert "Clear Boundaries vs Authentic Tails" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "privacy", "session", "explain"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
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
    res = subprocess.run([str(hscl_bin), "--json", "privacy", "tails", "verify", str(dummy_iso)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
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
        text=True, encoding="utf-8", errors="replace",
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
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_mismatch.returncode != 0
    assert "checksum mismatch" in (res_mismatch.stdout + res_mismatch.stderr).lower()

    # 4. Tails Launch --dry-run builds isolated QEMU command
    res_launch = subprocess.run(
        [str(hscl_bin), "--json", "privacy", "tails", "launch", str(dummy_iso), "--ram-mb", "8192", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
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
