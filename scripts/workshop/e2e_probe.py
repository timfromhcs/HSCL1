#!/usr/bin/env python3
"""Boot an ISO and run read-only shell commands INSIDE the live session through the Workshop API.

Usage: e2e_probe.py ISO OUTDIR COMMANDS.json      (COMMANDS.json: {"name": "shell command", ...})
Writes OUTDIR/probe.json with exit code and trimmed output per command. Read-only diagnostics; nothing is changed in the guest.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import e2e_respin as base  # noqa: E402
import vm as vmmod  # noqa: E402


def main() -> int:
    iso, out, cmds = sys.argv[1], Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"iso": Path(iso).name, "checks": {}}
    mgr = vmmod.VmManager(out / "vm")
    vm = mgr.start("probe", iso, None, 4096, "uefi")
    try:
        report["desktop_after_s"] = base.wait_desktop(vm)
        vm.rpc("status", timeout=180)
        time.sleep(20)
        for name, cmd in cmds.items():
            r = base.hook(vm, f"probe-{name}.sh", f"({cmd}) 2>&1 | head -c 6000; echo; echo \"__exit=$?\"\n", timeout=180)
            report["checks"][name] = {"hook_exit": r["exit"], "output": r["stdout"][-3500:]}
    finally:
        (out / "probe.json").write_text(json.dumps(report, indent=1))
        mgr.stop_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
