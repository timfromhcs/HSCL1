"""`hscl miner`: no public hosts, no silent flashing, dry runs write nothing."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

AUTH = "I am authorized to flash this device"


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    newest_src = max(
        (p.stat().st_mtime for p in (root / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0
    )
    for profile in ("debug", "release"):
        candidate = root / "target" / profile / exe
        # A stale target binary from an earlier source revision hides new subcommands; in that case
        # build through cargo instead of testing the old binary by accident.
        if candidate.is_file() and candidate.stat().st_mtime >= newest_src:
            return str(candidate)
    return "cargo"


def _run_hscl(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    bin_path = _find_hscl()
    cmd = ["cargo", "run", "-q", "-p", "hscl", "--"] + args if bin_path == "cargo" else [bin_path] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={**os.environ, **(env or {})},
    )


def test_status_is_read_only_and_mentions_the_phrase():
    res = _run_hscl(["miner", "status", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert "receiver_port" in data
    assert data["authorization_phrase"] == AUTH
    assert "no device is contacted" in data["note"]


def test_public_hosts_are_refused_by_probe_and_plan(tmp_path):
    fw = tmp_path / "esp-miner.bin"
    fw.write_bytes(b"x" * 64)
    for args in (
        ["miner", "probe", "8.8.8.8"],
        ["miner", "plan", "example.com", "--firmware", str(fw)],
    ):
        res = _run_hscl(args)
        assert res.returncode != 0, args
        assert "private" in (res.stdout + res.stderr).lower(), args


def test_plan_reports_size_hash_and_rollback_without_connecting(tmp_path):
    fw = tmp_path / "esp-miner.bin"
    fw.write_bytes(b"firmware" * 100)
    res = _run_hscl(["miner", "plan", "192.168.178.61", "--firmware", str(fw), "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["firmware_bytes"] == 800
    assert len(data["firmware_sha256"]) == 64
    assert data["url"] == "http://192.168.178.61/api/system/OTA"
    assert data["dry_run"] is True
    assert any("no TLS" in w for w in data["warnings"])


def test_ota_and_flash_refuse_without_the_exact_phrase(tmp_path):
    fw = tmp_path / "esp-miner.bin"
    fw.write_bytes(b"x" * 64)
    ota = _run_hscl(["miner", "ota", "192.168.178.61", "--firmware", str(fw), "--yes", "yes", "--dry-run"])
    assert ota.returncode != 0 and "authorized" in ota.stderr.lower()
    flash = _run_hscl(["miner", "flash", "--port", "COM5", "--offset", "0x10000", "--firmware", str(fw), "--yes", "yes", "--dry-run"])
    assert flash.returncode != 0 and "authorized" in flash.stderr.lower()


def test_dry_runs_print_the_command_and_write_nothing(tmp_path):
    fw = tmp_path / "esp-miner.bin"
    fw.write_bytes(b"x" * 64)
    cfg = tmp_path / "cfg"
    env = {"HSCL_CONFIG_DIR": str(cfg)}
    ota = _run_hscl(
        ["miner", "ota", "192.168.178.61", "--firmware", str(fw), "--yes", AUTH, "--dry-run"],
        env=env,
    )
    assert ota.returncode == 0, ota.stderr
    assert "nothing was sent" in ota.stdout
    assert not (cfg / "miner.json").exists(), "a dry run must not write configuration"
    flash = _run_hscl(
        ["miner", "flash", "--port", "COM5", "--offset", "0x10000", "--firmware", str(fw), "--yes", AUTH, "--dry-run", "--json"],
        env=env,
    )
    assert flash.returncode == 0, flash.stderr
    data = json.loads(flash.stdout)
    assert data["dry_run"] is True
    assert "write_flash" in data["argv"]
    assert "0x10000" in data["argv"]


def test_status_uses_the_override_config_dir_not_the_working_directory(tmp_path):
    cfg = tmp_path / "cfg"
    res = _run_hscl(["miner", "status", "--json"], env={"HSCL_CONFIG_DIR": str(cfg)})
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout)["config_dir"] == str(cfg)
