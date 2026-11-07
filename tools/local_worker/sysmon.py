#!/usr/bin/env python3
"""System monitor for benchmarks: samples Windows performance counters with `typeperf` and summarises CPU, GPU engines, GPU memory
and free RAM (owner request 2026-11-07: measure everything, balance CPU and iGPU load).

Counters used (all user-space, no driver install): per-PID `GPU Engine` utilisation (grouped by engine type, summed per sample),
`GPU Process Memory` Shared/Local/Dedicated usage, `Processor Information(_Total)` utility and performance, `Memory\\Available MBytes`.
Which engine type a Vulkan compute dispatch uses on this driver is recorded, not assumed. Blank samples are skipped, never counted
as zero. The balance figure compares the median CPU load with the busiest GPU engine; it describes load, not throughput.

Usage: python sysmon.py --seconds 10 [--pid PID]      (prints the JSON summary)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import math
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MB = 1048576.0
TS_FORMATS = ("%m/%d/%Y %H:%M:%S.%f", "%d.%m.%Y %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f")
SYSTEM_COUNTERS = (
    r"\Processor Information(_Total)\% Processor Utility",
    r"\Processor Information(_Total)\% Processor Performance",
    r"\Memory\Available MBytes",
)


def _oem_codec() -> str:
    if sys.platform.startswith("win"):
        import ctypes

        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    return "utf-8"


def perflib_tables() -> tuple[dict[str, int], dict[int, str]]:
    """(English name -> index, index -> name in the system UI language) from the Perflib registry data (Windows only).
    The classic CPU/memory counters are localized (German: \\Arbeitsspeicher\\Verfügbare MB); the GPU counters are not."""
    import ctypes
    import winreg

    def table(value: str) -> list[str]:
        v, _ = winreg.QueryValueEx(winreg.HKEY_PERFORMANCE_DATA, value)
        return v

    en_raw = table("Counter 009")
    en = {}
    for i in range(0, len(en_raw) - 1, 2):
        en.setdefault(en_raw[i + 1], int(en_raw[i]))
    try:
        lang = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF
        local_raw = table(f"Counter {lang:03X}")
    except OSError:
        local_raw = en_raw
    local = {int(local_raw[i]): local_raw[i + 1] for i in range(0, len(local_raw) - 1, 2)}
    return en, local


def localize_counter(path: str, en: dict[str, int], local: dict[int, str]) -> str:
    """Translate the object and counter name of `\\Object(instance)\\Counter`; instance names and unknown names stay as they are."""
    m = re.fullmatch(r"\\([^\\(]+)(\([^)]*\))?\\(.+)", path)
    if not m:
        return path
    obj, inst, ctr = m.group(1), m.group(2) or "", m.group(3)

    def tr(name: str) -> str:
        idx = en.get(name)
        return local.get(idx, name) if idx is not None else name

    return f"\\{tr(obj)}{inst}\\{tr(ctr)}"


def _reverse_counters(en: dict[str, int], local: dict[int, str]) -> tuple[dict[str, int], dict[int, str]]:
    """(local name -> index, index -> English name) for the reverse direction.

    Measured on the real German table: 1081 of 4774 local names belong to more than one index. With a plain
    `{name: idx}` comprehension the last one wins, and that index often has no English name - the counter then stayed German
    and disappeared from the summary (\\Memory\\Available MBytes resolved to index 1824 instead of 1382, so `ram_available_mb`
    was missing entirely). An index that the English table knows is therefore preferred over one it does not."""
    idx_to_en = {i: n for n, i in en.items()}
    back: dict[str, int] = {}
    for idx, name in local.items():
        if name not in back or (idx in idx_to_en and back[name] not in idx_to_en):
            back[name] = idx
    return back, idx_to_en


def delocalize_counter(path: str, en: dict[str, int], local: dict[int, str]) -> str:
    """Inverse of localize_counter: map a local-language counter path back to the English names used by summarize()."""
    back, idx_to_en = _reverse_counters(en, local)
    m = re.fullmatch(r"\\([^\\(]+)(\([^)]*\))?\\(.+)", path)
    if not m:
        return path
    obj, inst, ctr = m.group(1), m.group(2) or "", m.group(3)

    def tr(name: str) -> str:
        idx = back.get(name)
        return idx_to_en.get(idx, name) if idx is not None else name

    return f"\\{tr(obj)}{inst}\\{tr(ctr)}"


def counters_for_pid(pid: object) -> list[str]:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer")
    return [
        rf"\GPU Engine(pid_{pid}*)\Utilization Percentage",
        rf"\GPU Process Memory(pid_{pid}*)\Shared Usage",
        rf"\GPU Process Memory(pid_{pid}*)\Local Usage",
        rf"\GPU Process Memory(pid_{pid}*)\Dedicated Usage",
        *SYSTEM_COUNTERS,
    ]


def _number(s: str) -> float | None:
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        try:
            return float(s.replace(",", "."))  # German locale decimal comma
        except ValueError:
            return None


def parse_typeperf_csv(text: str) -> dict:
    # only quoted CSV records: typeperf appends plain status lines ("Exiting, please wait...") that contain commas
    data_lines = [ln for ln in text.splitlines() if ln.lstrip().startswith('"')]
    lines = [r for r in csv.reader(io.StringIO("\n".join(data_lines))) if len(r) > 1]
    if not lines:
        return {"columns": [], "rows": []}
    columns = [re.sub(r"^\\\\[^\\]+", "", c) for c in lines[0][1:]]
    rows = []
    for r in lines[1:]:
        vals = [_number(x) for x in r[1:]]
        vals += [None] * (len(columns) - len(vals))
        rows.append({"t": r[0], "values": vals[: len(columns)]})
    return {"columns": columns, "rows": rows}


def stats(values: list[float]) -> dict:
    v = sorted(values)
    if not v:
        return {"samples": 0}
    p95 = v[max(0, math.ceil(0.95 * len(v)) - 1)]
    return {"samples": len(v), "min": v[0], "median": statistics.median(v), "mean": round(statistics.fmean(v), 3), "p95": p95, "max": v[-1]}


def _ts(s: str) -> datetime.datetime | None:
    for f in TS_FORMATS:
        try:
            return datetime.datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def summarize(parsed: dict) -> dict:
    cols, rows = parsed["columns"], parsed["rows"]
    engines: dict[str, list[int]] = {}
    memory: dict[str, list[int]] = {}
    single: dict[str, int] = {}
    for i, c in enumerate(cols):
        m = re.search(r"GPU Engine\(.*engtype_([A-Za-z0-9_]+)\)\\Utilization Percentage", c)
        if m:
            engines.setdefault(m.group(1), []).append(i)
            continue
        m = re.search(r"GPU Process Memory\(.*\)\\(Shared|Local|Dedicated) Usage", c)
        if m:
            memory.setdefault(m.group(1).lower(), []).append(i)
        elif c.endswith(r"% Processor Utility"):
            single["cpu_utility"] = i
        elif c.endswith(r"% Processor Performance"):
            single["cpu_performance"] = i
        elif c.endswith(r"Available MBytes"):
            single["ram_available_mb"] = i

    def column(i: int) -> list[float]:
        return [r["values"][i] for r in rows if r["values"][i] is not None]

    def summed(idx: list[int], scale: float = 1.0) -> list[float]:
        out = []
        for r in rows:
            vals = [r["values"][i] for i in idx if r["values"][i] is not None]
            if vals:
                out.append(sum(vals) / scale)
        return out

    out: dict = {"samples": len(rows)}
    t0, t1 = (_ts(rows[0]["t"]), _ts(rows[-1]["t"])) if rows else (None, None)
    out["duration_s"] = round((t1 - t0).total_seconds(), 3) if t0 and t1 else None
    for name, i in single.items():
        out[name] = stats(column(i))
    out["gpu_engine_utilization"] = {k: stats(summed(v)) for k, v in sorted(engines.items())}
    out["gpu_memory_mb"] = {k: stats(summed(v, MB)) for k, v in sorted(memory.items())}
    return out


def balance(summary: dict) -> dict:
    cpu = float(summary.get("cpu_utility", {}).get("median", 0) or 0)
    gpus = [float(s.get("median", 0) or 0) for s in summary.get("gpu_engine_utilization", {}).values() if s.get("samples")]
    gpu = max(gpus) if gpus else 0.0
    hi = max(cpu, gpu)
    return {"cpu_median": cpu, "gpu_median": gpu, "ratio_min_over_max": round(min(cpu, gpu) / hi, 3) if hi > 0 else 0.0}


class Monitor:
    """Background typeperf sampler. If the GPU counters do not exist yet (no instance for the PID) typeperf exits at once; the monitor
    then falls back to the system counters and sets `degraded`."""

    def __init__(self, pid: int | None = None, interval: int = 1):
        self.pid, self.interval, self.degraded = pid, interval, False
        self._proc: subprocess.Popen | None = None
        self._file = None
        self._tables: tuple[dict[str, int], dict[int, str]] | None = None
        if sys.platform.startswith("win"):
            try:
                self._tables = perflib_tables()
            except OSError:
                self._tables = None  # fall back to English names (works on English Windows)

    def _spawn(self, counters: list[str]) -> None:
        if self._tables:
            counters = [localize_counter(c, *self._tables) for c in counters]
        self._file = tempfile.TemporaryFile(mode="w+b")  # typeperf writes the console (OEM) code page, not UTF-8
        # own process group so that CTRL_BREAK reaches only typeperf, which then flushes its buffered output before exiting
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform.startswith("win") else 0
        self._proc = subprocess.Popen(["typeperf", "-si", str(self.interval), *counters], stdout=self._file, stderr=subprocess.DEVNULL, creationflags=flags)

    def start(self) -> "Monitor":
        self._spawn(counters_for_pid(self.pid) if self.pid else list(SYSTEM_COUNTERS))
        time.sleep(1.5)
        if self.pid and self._proc.poll() is not None:
            self.degraded = True
            self._spawn(list(SYSTEM_COUNTERS))
        return self

    def stop(self) -> dict:
        assert self._proc is not None and self._file is not None
        if self._proc.poll() is None:
            if sys.platform.startswith("win"):
                self._proc.send_signal(signal.CTRL_BREAK_EVENT)  # graceful: typeperf flushes what it has sampled
            else:
                self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._file.seek(0)
        parsed = parse_typeperf_csv(self._file.read().decode(_oem_codec(), errors="replace"))
        if self._tables:
            parsed["columns"] = [delocalize_counter(c, *self._tables) for c in parsed["columns"]]
        summary = summarize(parsed)
        summary["gpu_counters_degraded"] = self.degraded
        summary["balance"] = balance(summary)
        return summary


def sample_system(seconds: int = 5, pid: int | None = None) -> dict:
    m = Monitor(pid).start()
    time.sleep(max(1, seconds))
    return m.stop()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seconds", type=int, default=5)
    ap.add_argument("--pid", type=int, default=None)
    a = ap.parse_args(argv)
    print(json.dumps(sample_system(a.seconds, a.pid), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
