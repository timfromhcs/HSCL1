#!/usr/bin/env python3
"""Boot an ISO and run `hscl graphics apply` and `hscl wallpaper apply` against the REAL Plasma session in the VM,
with a screenshot after every step. Usage: e2e_apply.py ISO OUTDIR  -> OUTDIR/apply-report.json + PNGs."""
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

ENV = "export XDG_RUNTIME_DIR=/run/user/$(id -u); export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus; "
STEPS = [
    ("anim_before", "kreadconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor; echo \"(empty = default 1)\""),
    ("graphics_apply", "hscl graphics apply --force --json"),
    ("anim_after", "kreadconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor"),
    ("blur_after", "kreadconfig6 --file kwinrc --group Plugins --key blurEnabled"),
    ("wp_aurora", "hscl wallpaper apply aurora --json"),
    ("wp_grid", "hscl wallpaper apply grid-pulse --json"),
    ("wp_starfield", "hscl wallpaper apply starfield --json"),
    ("wp_rain", "hscl wallpaper apply midnight-rain --json"),
]


def main() -> int:
    iso, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"steps": {}}
    mgr = vmmod.VmManager(out / "vm")
    vm = mgr.start("apply", iso, None, 4096, "uefi")
    try:
        report["desktop_after_s"] = base.wait_desktop(vm)
        vm.rpc("status", timeout=180)
        time.sleep(15)
        (out / "00-before.png").write_bytes(base.rgb_shot(vm)[0])
        for name, cmd in STEPS:
            script = f"runuser -l kubuntu -c '{ENV}{cmd}' 2>&1 | head -c 3000; echo; echo \"__exit=$?\"\n"
            try:
                r = base.hook(vm, f"ap-{name.replace('_', '-')}.sh", script, timeout=120)
                report["steps"][name] = r["stdout"].strip()[-1500:]
            except Exception as e:  # noqa: BLE001
                report["steps"][name] = f"ERROR {type(e).__name__}: {e}"
            time.sleep(6)
            (out / f"{len(report['steps']):02d}-{name}.png").write_bytes(base.rgb_shot(vm)[0])
    finally:
        (out / "apply-report.json").write_text(json.dumps(report, indent=1))
        mgr.stop_all()
    print(json.dumps({k: v[:120].replace("\n", " ") for k, v in report["steps"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
