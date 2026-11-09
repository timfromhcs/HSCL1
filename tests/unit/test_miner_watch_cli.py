"""`hscl miner watch`: private hosts only, and a dead endpoint must not hang forever."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


def _find_hscl() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    exe = "hscl.exe" if os.name == "nt" else "hscl"
    newest = max((p.stat().st_mtime for p in (root / "cli" / "hscl" / "src").rglob("*.rs")), default=0.0)
    for profile in ("debug", "release"):
        candidate = root / "target" / profile / exe
        if candidate.is_file() and candidate.stat().st_mtime >= newest:
            return str(candidate)
    return "cargo"


def _run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    binary = _find_hscl()
    cmd = ["cargo", "run", "-q", "-p", "hscl", "--"] + args if binary == "cargo" else [binary] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, timeout=timeout,
    )


def test_a_public_host_is_refused_before_any_socket():
    res = _run(["miner", "watch", "1.1.1.1", "--seconds", "1"])
    assert res.returncode != 0
    assert "private" in res.stderr.lower()


def test_a_closed_port_fails_instead_of_hanging():
    started = time.time()
    res = _run(["miner", "watch", "127.0.0.1", "--seconds", "1", "--path", "/api/ws/live"])
    assert time.time() - started < 30
    assert res.returncode != 0
    assert "connect" in (res.stderr + res.stdout).lower()
