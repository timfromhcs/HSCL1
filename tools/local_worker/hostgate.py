#!/usr/bin/env python3
"""Host gate, single-flight lock and residency-aware memory cost for the local delegate (plan 2026-11-07-local-agents-v2, Track 1).

Why (measured 2026-11-07): two local_code runs plus a QEMU VM drove the host to CPU 100 % and 2.7 GB free RAM and froze the guests;
the shared 8080 server costs about 1.3 GB asleep and 2.7-3.5 GB working, so treating it as 0 MB hid the real cost.

Pure decision functions take their inputs as arguments; the probes at the bottom read the real machine (Windows and Linux, stdlib only).
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Mapping

DEFAULT_CPU_LIMIT = 85.0


class Busy(Exception):
    """Another local task holds the single-flight lock."""


def decide_host(
    cpu_pct: float,
    qemu_running: bool,
    free_mb: int,
    need_mb: int,
    reserve_mb: int,
    cpu_limit: float = DEFAULT_CPU_LIMIT,
    allow_vm: bool = False,
) -> dict:
    """Refuse a model run when a VM is running, the CPU is saturated or memory is short. Memory is never overridable."""
    if min(cpu_pct, free_mb, need_mb, reserve_mb) < 0:
        raise ValueError("values must not be negative")
    needed = need_mb + reserve_mb
    if free_mb < needed:
        return {"ok": False, "reason": f"short by {needed - free_mb} MiB (need {needed}, available {free_mb})"}
    if qemu_running and not allow_vm:
        return {"ok": False, "reason": "a VM is running (qemu); stop it first or set HSCL_WORKER_ALLOW_VM=1"}
    if cpu_pct > cpu_limit:
        return {"ok": False, "reason": f"CPU is busy ({cpu_pct:.0f} % over the sample, limit {cpu_limit:.0f} %)"}
    return {"ok": True, "reason": "host idle enough"}


def effective_model_mb(
    model: str,
    table: Mapping[str, int],
    wake_mb: Mapping[str, int],
    process: Mapping[str, str],
    resident_mb: Callable[[str], int],
    default_mb: int = 6000,
    resident_threshold_mb: int = 2000,
) -> int:
    """Memory a run adds. A shared server that is already working (resident above the threshold) adds nothing; asleep or absent it adds its wake cost."""
    base = table.get(model, default_mb)
    if model in wake_mb and model in process:
        return 0 if resident_mb(process[model]) >= resident_threshold_mb else wake_mb[model]
    return base


class SingleFlight:
    """Cross-process single-flight lock: a file holding the owner's PID; a dead owner or garbage content is taken over."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._held = False

    @staticmethod
    def _alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if sys.platform.startswith("win"):
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True, errors="replace").stdout
            return str(pid) in out
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _stale(self) -> bool:
        try:
            pid = int(json.loads(self.path.read_text(encoding="utf-8"))["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            return True
        return not self._alive(pid)

    def __enter__(self) -> "SingleFlight":
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._stale():
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                raise Busy("another local task is running") from None
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "t": time.time()}, f)
            self._held = True
            return self
        raise Busy("lock could not be taken")

    def __exit__(self, *exc) -> None:
        if self._held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._held = False


# ---- real probes (not unit tested; exercised by the tool itself) --------------------------------------------------------------------
class _FileTime(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_ulong), ("hi", ctypes.c_ulong)]


def _ft(x: _FileTime) -> int:
    return (x.hi << 32) | x.lo


def cpu_percent(sample_s: float = 0.6) -> float:
    """Whole-machine CPU load over a short sample."""
    if sys.platform.startswith("win"):
        idle, kern, user = _FileTime(), _FileTime(), _FileTime()
        k = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        a = (_ft(idle), _ft(kern), _ft(user))
        time.sleep(sample_s)
        k.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        b = (_ft(idle), _ft(kern), _ft(user))
        total = (b[1] - a[1]) + (b[2] - a[2])  # kernel time includes idle
        busy = total - (b[0] - a[0])
        return max(0.0, min(100.0, 100.0 * busy / total)) if total > 0 else 0.0

    def read() -> tuple[int, int]:
        f = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        v = [int(x) for x in f]
        return v[3] + (v[4] if len(v) > 4 else 0), sum(v)

    i0, t0 = read()
    time.sleep(sample_s)
    i1, t1 = read()
    return max(0.0, min(100.0, 100.0 * (1 - (i1 - i0) / (t1 - t0)))) if t1 > t0 else 0.0


def _tasklist(name: str) -> list[list[str]]:
    import csv

    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}.exe", "/NH", "/FO", "CSV"], capture_output=True, text=True, errors="replace").stdout
    return [r for r in csv.reader(out.splitlines()) if r and r[0].lower().startswith(name.lower())]


def process_running(name: str) -> bool:
    if sys.platform.startswith("win"):
        return bool(_tasklist(name))
    return subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0


def process_rss_mb(name: str) -> int:
    """Largest resident set among processes with that name (0 if none)."""
    best = 0
    if sys.platform.startswith("win"):
        for r in _tasklist(name):
            digits = "".join(ch for ch in r[4] if ch.isdigit()) if len(r) > 4 else ""
            best = max(best, int(digits) // 1024 if digits else 0)  # tasklist reports KB
        return best
    out = subprocess.run(["ps", "-C", name, "-o", "rss="], capture_output=True, text=True, errors="replace").stdout.split()
    return max((int(x) // 1024 for x in out), default=0)


def qemu_running() -> bool:
    return process_running("qemu-system-x86_64")
