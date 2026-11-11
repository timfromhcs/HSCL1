#!/usr/bin/env python3
"""Q-61 discriminator: does the installer die when it is *not* started from a session scope?

The installer is killed in roughly one start in six to twelve, 2-3 s after it opens, with no OOM and no
core file. The open question is who signals it. This probe starts the same binary twice - detached with
`setsid` (no controlling terminal, its own session) and as a direct child of the hook shell - five times
each, and records how many are still alive after 10 s.

  both die      -> the killer is inside the process tree (Calamares/KCrash)
  only direct   -> the killer is the launching context (session/scope/cgroup)

Usage: python scripts/dev/probe_installer_kill.py --iso ISO [--mem 3072] [--runs 5]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
import vm as vmmod  # noqa: E402
import e2e_respin as respin  # noqa: E402

LAUNCH = "/usr/bin/calamares-launch-normal"


def series(kind: str, runs: int) -> str:
    if kind == "detached":
        start = f"sudo -b setsid {LAUNCH} </dev/null >/dev/null 2>&1"
    else:
        start = f"sudo -b {LAUNCH} </dev/null >/dev/null 2>&1"
    return f"""
set -u
for i in $(seq 1 {runs}); do
  {start}
  sleep 10
  alive=$(pgrep -c -x calamares || true)
  echo "{kind} $i alive=$alive"
  sudo pkill -f calamares-launch-normal >/dev/null 2>&1 || true
  sudo pkill -x calamares >/dev/null 2>&1 || true
  sleep 4
done
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--mem", type=int, default=3072)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "probe-installer-kill"))
    a = ap.parse_args()

    iso = Path(a.iso)
    if not iso.is_file():
        print(f"iso not found: {iso}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    mgr = vmmod.VmManager(out / "vm_work", mem_guard=False)
    vm = mgr.start("killprobe", str(iso), None, memory_mb=a.mem, firmware="uefi")
    report: dict = {"iso": iso.name, "runs_per_context": a.runs, "series": {}}
    try:
        print("waiting for desktop...", flush=True)
        report["desktop_s"] = respin.wait_desktop(vm, timeout=420)
        for kind in ("detached", "direct"):
            print(f"--- {kind} ---", flush=True)
            res = respin.hook(vm, f"{kind}.sh", series(kind, a.runs), timeout=60 + 20 * a.runs)
            print(res.get("stdout", ""), flush=True)
            report["series"][kind] = {
                "exit": res.get("exit"),
                "stdout": res.get("stdout", ""),
                "stderr": res.get("stderr", ""),
            }
        png = vm.screenshot_png()
        if png:
            (out / "final.png").write_bytes(png)
    finally:
        report["finished_at"] = time.time()
        (out / "probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"report: {out / 'probe.json'}", flush=True)
        try:
            mgr.stop_all()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
