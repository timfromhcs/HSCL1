"""`hscl miner pool`: slot validation, masking and dry-run safety."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

AUTH = "I am authorized to flash this device"


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    newest = max((p.stat().st_mtime for p in (root / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0)
    for profile in ("debug", "release"):
        candidate = root / "target" / profile / exe
        if candidate.is_file() and candidate.stat().st_mtime >= newest:
            return str(candidate)
    return "cargo"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    binary = _find_hscl()
    cmd = ["cargo", "run", "-q", "-p", "hscl", "--"] + args if binary == "cargo" else [binary] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )


def test_set_dry_run_is_masked_and_writes_nothing():
    res = _run(
        [
            "miner", "pool", "set", "192.168.178.61",
            "--index", "0", "--url", "solo.ckpool.org", "--port", "3333",
            "--user", "bc1qexampleaddress0000000000000000",
            "--yes", AUTH, "--dry-run", "--json",
        ]
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["dry_run"] is True
    assert "nothing" in res.stdout.lower() or data["endpoint"].startswith("PUT ")
    assert "bc1qexampleaddress" not in res.stdout
    assert "<set>" in res.stdout


def test_validation_rejects_bad_slots_and_schemes():
    for bad in (
        ["--index", "9", "--url", "pool", "--port", "3333", "--user", "a"],
        ["--index", "0", "--url", "stratum+tcp://pool", "--port", "3333", "--user", "a"],
        ["--index", "0", "--url", "pool", "--port", "0", "--user", "a"],
        ["--index", "0", "--url", "pool", "--port", "3333", "--user", "a", "--protocol", "SV9"],
        ["--index", "0", "--url", "pool", "--port", "3333", "--user", ""],
    ):
        res = _run(["miner", "pool", "set", "192.168.178.61", *bad, "--yes", AUTH, "--dry-run"])
        assert res.returncode != 0, bad


def test_the_phrase_and_private_host_are_required():
    base = ["miner", "pool", "set", "192.168.178.61", "--index", "0", "--url", "pool",
            "--port", "3333", "--user", "a", "--dry-run"]
    res = _run(base + ["--yes", "yes"])
    assert res.returncode != 0 and "authorized" in res.stderr.lower()
    res = _run(["miner", "pool", "set", "1.1.1.1", *base[4:], "--yes", AUTH])
    assert res.returncode != 0 and "private" in res.stderr.lower()
