"""Tests for `hscl security` CLI subcommands (AGENTS.md section 6.1 & 8.2)."""
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


def test_security_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "AppArmor enabled:" in res.stdout
    assert "UFW enabled:" in res.stdout
    assert "Secure Boot:" in res.stdout
    assert "LUKS volumes open:" in res.stdout
    assert "Forbidden APT repos:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "apparmor" in data
    assert "firewall_ufw_enabled" in data
    assert "secure_boot" in data
    assert "luks_mapped_devices" in data
    assert "forbidden_apt_sources" in data


def test_security_firewall_status_and_profiles(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "firewall", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "ufw service:" in res.stdout
    assert "default incoming:" in res.stdout
    assert "active profile:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "firewall", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "enabled" in data
    assert "default_incoming" in data
    assert "active_profile" in data
    assert "standard" in data["profiles_available"]
    assert "public-wifi" in data["profiles_available"]
    assert "lab" in data["profiles_available"]
    assert "privacy" in data["profiles_available"]


def test_security_firewall_profile_list_and_set_dry_run(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "firewall", "profile", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "standard" in res.stdout
    assert "public-wifi" in res.stdout
    assert "lab" in res.stdout
    assert "privacy" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "firewall", "profile", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "profiles" in data
    names = [p["name"] for p in data["profiles"]]
    assert names == ["standard", "public-wifi", "lab", "privacy"]

    # Dry-run for standard
    res_std = subprocess.run(
        [str(hscl_bin), "--json", "security", "firewall", "profile", "set", "standard", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_std.returncode == 0
    data_std = json.loads(res_std.stdout)
    assert data_std["dry_run"] is True
    assert data_std["profile"] == "standard"
    assert any("default deny incoming" in c for c in data_std["commands"])

    # Dry-run for privacy
    res_priv = subprocess.run(
        [str(hscl_bin), "--json", "security", "firewall", "profile", "set", "privacy", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_priv.returncode == 0
    data_priv = json.loads(res_priv.stdout)
    assert any("default reject outgoing" in c for c in data_priv["commands"])
    assert any("9001" in c for c in data_priv["commands"])


def test_security_apparmor_status(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "apparmor", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "AppArmor:" in res.stdout
    assert "profiles loaded:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "apparmor", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "enabled" in data
    assert "profiles_loaded" in data
    assert "enforce_mode" in data
    assert "complain_mode" in data


def test_security_audit_and_report_file(hscl_bin: Path, tmp_path: Path):
    res = subprocess.run([str(hscl_bin), "security", "audit"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "HSCL1 Security Posture Audit" in res.stdout
    assert "AppArmor:" in res.stdout
    assert "UFW Firewall:" in res.stdout
    assert "Verdict:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "audit"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "apparmor" in data
    assert "firewall" in data
    assert "secure_boot" in data
    assert "encryption" in data
    assert "suid_dumpable_secure" in data
    assert "overall_verdict" in data

    # Write report file
    report_file = tmp_path / "audit_report.json"
    res_file = subprocess.run(
        [str(hscl_bin), "security", "audit", "--output", str(report_file)],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_file.returncode == 0
    assert report_file.is_file()
    saved = json.loads(report_file.read_text(encoding="utf-8"))
    assert "overall_verdict" in saved

    # Refuse overwrite
    res_overwrite = subprocess.run(
        [str(hscl_bin), "security", "audit", "--output", str(report_file)],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_overwrite.returncode != 0
    assert "refusing to overwrite" in (res_overwrite.stdout + res_overwrite.stderr).lower()


def test_security_encryption_status(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "encryption", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "LUKS mapped volumes:" in res.stdout
    assert "Root encrypted:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "encryption", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "luks_mapped_volumes" in data
    assert "crypttab_entries" in data
    assert "root_is_encrypted" in data


def test_security_recovery_check(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "security", "recovery", "check"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "backup directories:" in res.stdout
    assert "snapshots found:" in res.stdout
    assert "notice:" in res.stdout

    res_j = subprocess.run([str(hscl_bin), "--json", "security", "recovery", "check"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_j.returncode == 0
    data = json.loads(res_j.stdout)
    assert "backup_dir_exists" in data
    assert "snapshots_found" in data
    assert "notice" in data
