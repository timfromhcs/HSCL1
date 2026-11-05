#!/usr/bin/env python3
"""Boot an ISO and run the HSCL1 CLI and system checks INSIDE the live session through the Workshop API.

Usage: e2e_cli.py ISO OUTDIR
Writes OUTDIR/cli-report.json: for every check the exit code and the (trimmed) output, plus a desktop screenshot.
Nothing is assumed: a check that was not run or failed is recorded as such.
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

AS_USER = "runuser -l kubuntu -c"
CHECKS = {
    # system-level state created by the packages
    "earlyoom_active": "systemctl is-active earlyoom",
    "zram_swap": "swapon --show --noheadings",
    "zram_algorithm": "cat /sys/block/zram0/comp_algorithm 2>&1 | head -c 200",
    "sysctl_memory": "sysctl vm.swappiness vm.page-cluster",
    "ai_slice": "systemctl show hscl-ai.slice -p MemoryHigh -p MemoryMax",
    "firewall": "ufw status | head -n 3",
    "listening_sockets": "ss -tulnH | awk '{print $1, $5}'",
    # CLI as the desktop user
    "hscl_version": f"{AS_USER} 'hscl version --json'",
    "memory_status": f"{AS_USER} 'hscl memory status --json'",
    "memory_budget": f"{AS_USER} 'hscl memory budget'",
    "graphics_detect": f"{AS_USER} 'hscl graphics detect --json'",
    "ai_model_list": f"{AS_USER} 'hscl ai model list --json'",
    "ai_profile": f"{AS_USER} 'hscl ai profile --json'",
    "wallpaper_list": f"{AS_USER} 'hscl wallpaper list --json'",
    "wallpaper_dry_run": f"{AS_USER} 'hscl wallpaper apply midnight-rain --dry-run --json'",
    "code_list": f"{AS_USER} 'hscl code list --json'",
    "updates_check": f"{AS_USER} 'hscl system updates --check --json'",
    "mcp_roundtrip": ("printf '%s\\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}' "
                      "'{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}' "
                      f"'{{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{{\"name\":\"hscl_version\",\"arguments\":{{}}}}}}' | {AS_USER} 'hscl mcp'"),
}


def main() -> int:
    iso, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"iso": Path(iso).name, "checks": {}}
    mgr = vmmod.VmManager(out / "vm")
    vm = mgr.start("cli", iso, None, 4096, "uefi")
    try:
        report["desktop_after_s"] = base.wait_desktop(vm)
        report["status"] = vm.rpc("status", timeout=180)
        time.sleep(20)  # let the session settle (services, plasma)
        for name, cmd in CHECKS.items():
            script = f"({cmd}) 2>&1 | head -c 6000; echo; echo \"__exit=$?\"\n"
            try:
                r = base.hook(vm, f"chk-{name.replace('_', '-')}.sh", script, timeout=180)
                text = r["stdout"]
                report["checks"][name] = {"hook_exit": r["exit"], "output": text[-3500:]}
            except Exception as e:  # noqa: BLE001 - record, do not hide
                report["checks"][name] = {"error": f"{type(e).__name__}: {e}"}
        report["screenshot_png"] = (out / "desktop.png").name
        (out / "desktop.png").write_bytes(base.rgb_shot(vm)[0])
    finally:
        (out / "cli-report.json").write_text(json.dumps(report, indent=1))
        mgr.stop_all()
    bad = [k for k, v in report["checks"].items() if "error" in v]
    print(json.dumps({"desktop_after_s": report.get("desktop_after_s"), "checks_run": len(report["checks"]), "errors": bad}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
