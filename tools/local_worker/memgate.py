#!/usr/bin/env python3
"""Free-RAM gate for local model starts (plan L, task L2).

Policy from the research: do not start a model when available RAM is below model + KV estimate + a reserve (default 3000 MiB)
that keeps the desktop, WSL2 and QEMU usable. Available memory (not "free") is the right number: standby cache counts.

Usage: python memgate.py MODEL_MB KV_MB   (exit 0 = ok to start, 1 = refuse, prints the reason)
"""
from __future__ import annotations

import ctypes
import re
import sys
from pathlib import Path

DEFAULT_RESERVE_MB = 3000


def can_start(model_mb: int, kv_mb: int, free_mb: int, reserve_mb: int = DEFAULT_RESERVE_MB) -> bool:
    return decide(model_mb, kv_mb, free_mb, reserve_mb)["ok"]


def decide(model_mb: int, kv_mb: int, free_mb: int, reserve_mb: int = DEFAULT_RESERVE_MB) -> dict:
    if min(model_mb, kv_mb, free_mb, reserve_mb) < 0:
        raise ValueError("memory values must not be negative")
    needed = model_mb + kv_mb + reserve_mb
    ok = free_mb >= needed
    reason = "enough available RAM" if ok else f"short by {needed - free_mb} MiB (need {needed}, available {free_mb})"
    return {"ok": ok, "needed_mb": needed, "free_mb": free_mb, "reserve_mb": reserve_mb, "reason": reason}


def parse_meminfo(text: str) -> int:
    m = re.search(r"^MemAvailable:\s+(\d+)\s+kB", text, re.M)
    if not m:
        raise ValueError("MemAvailable not found")
    return int(m.group(1)) // 1024


class _MemStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def free_mb() -> int:
    """Available physical memory in MiB (Windows: GlobalMemoryStatusEx; Linux: /proc/meminfo)."""
    if sys.platform.startswith("win"):
        st = _MemStatus()
        st.dwLength = ctypes.sizeof(_MemStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):  # type: ignore[attr-defined]
            raise OSError("GlobalMemoryStatusEx failed")
        return int(st.ullAvailPhys // (1024 * 1024))
    return parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 2 or not all(x.isdigit() for x in a):
        print("usage: memgate.py MODEL_MB KV_MB", file=sys.stderr)
        return 2
    d = decide(int(a[0]), int(a[1]), free_mb())
    print(d["reason"])
    return 0 if d["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
