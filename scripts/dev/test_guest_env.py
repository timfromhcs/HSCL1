#!/usr/bin/env python3
"""Inspect guest environment and test interactive GUI launching."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
import qemu_boot_test as q  # noqa: E402
import vm as vmmod  # noqa: E402
import e2e_respin as respin  # noqa: E402


def run_cmd(vm, cmd: str) -> dict:
    hook_script = f"#!/bin/bash\n{cmd}\n"
    hook_name = f"hook-{int(time.time()*1000)}.sh"
    return respin.hook(vm, hook_name, hook_script, timeout=30)


def take_shot(vm, path: Path) -> Path:
    png = vm.screenshot_png()
    path.write_bytes(png)
    im = Image.open(path)
    colors = len(im.getcolors(maxcolors=200000) or [])
    print(f"[SHOT] {path.name}: {len(png)} bytes, {colors} colors, size={im.size}", flush=True)
    return path


def main() -> int:
    iso = Path(r"\\wsl.localhost\Ubuntu\home\tim\hscl1-build\out\HSCL1-0.1.3-alpha.0-amd64.iso")
    out_dir = ROOT / "artifacts" / "test_gui_diag"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Testing Guest Environment & GUI Launch ===")
    mgr = vmmod.VmManager(out_dir / "vm_work", mem_guard=False)
    vm = mgr.start("diag", str(iso), None, memory_mb=3072, firmware="uefi")
    try:
        print("Waiting for live desktop...", flush=True)
        desktop_s = respin.wait_desktop(vm, timeout=360)
        print(f"Desktop reached after {desktop_s}s", flush=True)

        take_shot(vm, out_dir / "01_initial_desktop.png")

        # Check running processes and environment
        diag_cmd = """
        echo "=== WHOAMI & ID ==="
        id
        echo "=== LOGGED IN USERS ==="
        who
        loginctl list-sessions
        echo "=== WAYLAND SOCKETS ==="
        ls -la /run/user/1000/wayland* 2>&1 || true
        echo "=== DBUS SOCKETS ==="
        ls -la /run/user/1000/bus 2>&1 || true
        echo "=== PLASMA PROCESSES ==="
        ps aux | grep -E "plasma|kwin|sddm|wayland" | head -n 20
        """
        r = run_cmd(vm, diag_cmd)
        print("Guest Diag Output:\n", r.get("output", r))

        # Test launching konsole via systemd-run or sudo with full env
        test_launch = """
        sudo -u hscl1 env WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus nohup konsole > /tmp/konsole.log 2>&1 &
        sleep 2
        ps aux | grep konsole
        cat /tmp/konsole.log || true
        """
        r2 = run_cmd(vm, test_launch)
        print("Konsole Launch Output:\n", r2.get("output", r2))

        time.sleep(3)
        take_shot(vm, out_dir / "02_after_konsole.png")

        # Now test QMP keyboard input into Konsole
        print("Testing QMP typing into Konsole...", flush=True)
        q.type_text(vm.qmp, "hscl status\n")
        time.sleep(3)
        take_shot(vm, out_dir / "03_after_typing_status.png")

    finally:
        print("Stopping VM...", flush=True)
        mgr.stop_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
